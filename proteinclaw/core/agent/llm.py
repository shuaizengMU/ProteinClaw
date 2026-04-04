from __future__ import annotations
import json
from typing import Any, AsyncGenerator, Generator
import litellm
from proteinclaw.core.config import SUPPORTED_MODELS


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
    cfg = SUPPORTED_MODELS.get(model, {})
    provider = cfg.get("provider", "")

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
