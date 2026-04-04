from __future__ import annotations
import json
import os
import time
from typing import Any, AsyncGenerator, Generator
import httpx
import litellm
from proteinclaw.core.config import SUPPORTED_MODELS


# Cached Copilot session token (short-lived JWT).
_copilot_session: dict[str, Any] = {"token": "", "expires_at": 0}


def _get_copilot_session_token() -> str:
    """Exchange the stored GitHub OAuth token for a fresh Copilot session token."""
    oauth_token = os.environ.get("GITHUB_COPILOT_TOKEN", "")
    if not oauth_token:
        raise ValueError("GITHUB_COPILOT_TOKEN is not set")

    # Reuse cached token if still valid (with 60s margin).
    if _copilot_session["token"] and _copilot_session["expires_at"] > time.time() + 60:
        return _copilot_session["token"]

    resp = httpx.get(
        "https://api.github.com/copilot_internal/v2/token",
        headers={
            "Authorization": f"token {oauth_token}",
            "User-Agent": "ProteinClaw/1.0",
            "Accept": "application/json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    _copilot_session["token"] = data["token"]
    _copilot_session["expires_at"] = data.get("expires_at", time.time() + 600)
    return _copilot_session["token"]


def build_tools_schema(tools: dict) -> list[dict]:
    """Convert TOOL_REGISTRY entries to OpenAI function-calling schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools.values()
    ]


def _get_litellm_kwargs(model: str) -> dict[str, Any]:
    # Reload config so that API keys saved after the server started are picked up.
    from proteinclaw.core.config import load_user_config
    load_user_config()

    cfg = SUPPORTED_MODELS.get(model, {})
    provider = cfg.get("provider", "")

    # GitHub Copilot models: strip "copilot/" prefix, get a fresh session token,
    # and route via the openai provider with custom api_base.
    if model.startswith("copilot/"):
        real_model = model[len("copilot/"):]
        session_token = _get_copilot_session_token()
        kwargs: dict[str, Any] = {
            "model": f"openai/{real_model}",
            "api_base": cfg.get("api_base", "https://api.githubcopilot.com"),
            "api_key": session_token,
            "extra_headers": {
                "Copilot-Integration-Id": "vscode-chat",
                "Editor-Version": "vscode/1.100.0",
                "Editor-Plugin-Version": "copilot-chat/0.25.0",
            },
        }
        return kwargs

    # litellm recognises OpenAI and Anthropic model names natively.
    # Other providers need a "provider/" prefix.
    # Models that already contain "/" (e.g. "ollama/llama3") are used as-is.
    if "/" in model or provider in ("openai", "anthropic", ""):
        litellm_model = model
    else:
        litellm_model = f"{provider}/{model}"

    kwargs: dict[str, Any] = {"model": litellm_model}
    if "api_base" in cfg:
        kwargs["api_base"] = cfg["api_base"]
    return kwargs


def call_llm(model: str, messages: list[dict], tools: list[dict]):
    """Single (non-streaming) LLM call. Returns the response message object."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(
        messages=messages,
        tools=tools or None,
        tool_choice="auto" if tools else None,
        **kwargs,
    )
    return response.choices[0].message


async def call_llm_async_stream(
    model: str,
    messages: list[dict],
    tools: list[dict],
) -> AsyncGenerator[tuple[str, Any], None]:
    """Async streaming LLM call with tool support.

    Yields:
      ('token', str)           — content delta from the model
      ('tool_calls', list)     — accumulated tool calls once streaming ends
    """
    kwargs = _get_litellm_kwargs(model)
    tool_buf: dict[int, dict[str, str]] = {}

    response = await litellm.acompletion(
        messages=messages,
        tools=tools or None,
        tool_choice="auto" if tools else None,
        stream=True,
        **kwargs,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            yield ("token", delta.content)
        for tc in getattr(delta, "tool_calls", None) or []:
            idx = tc.index
            if idx not in tool_buf:
                tool_buf[idx] = {"id": "", "name": "", "arguments": ""}
            if tc.id:
                tool_buf[idx]["id"] = tc.id
            if tc.function:
                if tc.function.name:
                    tool_buf[idx]["name"] += tc.function.name
                if tc.function.arguments:
                    tool_buf[idx]["arguments"] += tc.function.arguments

    if tool_buf:
        yield ("tool_calls", [tool_buf[k] for k in sorted(tool_buf)])


def call_llm_stream(model: str, messages: list[dict]) -> Generator[str, None, None]:
    """Streaming LLM call (no tools). Yields text tokens."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(messages=messages, stream=True, **kwargs)
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
