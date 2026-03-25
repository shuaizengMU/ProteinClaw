from __future__ import annotations
import json
from typing import Any, Generator
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
    kwargs: dict[str, Any] = {"model": model}
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


def call_llm_stream(model: str, messages: list[dict]) -> Generator[str, None, None]:
    """Streaming LLM call (no tools). Yields text tokens."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(messages=messages, stream=True, **kwargs)
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
