from __future__ import annotations
import json
from typing import AsyncGenerator
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY
from proteinclaw.core.agent.llm import call_llm_async_stream, build_tools_schema
from proteinclaw.core.agent.prompt import build_system_prompt
from proteinclaw.core.agent.events import (
    Event, ToolCallEvent, ObservationEvent, TokenEvent, DoneEvent, ErrorEvent
)


async def run(
    query: str,
    history: list[dict],
    model: str,
    max_steps: int = 10,
) -> AsyncGenerator[Event, None]:
    """
    Run the ReAct agent loop. Yields typed Event objects.
    Consumer calls event.to_dict() to get the WebSocket-compatible dict.
    """
    tools = discover_tools()
    tools_schema = build_tools_schema(tools)
    system_prompt = build_system_prompt(tools)

    messages: list[dict] = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": query}]
    )

    for step in range(max_steps):
        tool_calls_received: list[dict] | None = None

        async for kind, data in call_llm_async_stream(
            model=model, messages=messages, tools=tools_schema
        ):
            if kind == "token":
                yield TokenEvent(content=data)
            elif kind == "tool_calls":
                tool_calls_received = data

        if tool_calls_received is None:
            # No tool calls — final answer already streamed token by token.
            yield DoneEvent()
            return

        # Assistant turn: record the tool calls in message history.
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls_received
            ],
        })

        for tc in tool_calls_received:
            tool_name = tc["name"]
            try:
                args = json.loads(tc["arguments"])
            except json.JSONDecodeError:
                args = {}

            yield ToolCallEvent(tool=tool_name, args=args)

            tool = tools.get(tool_name)
            if tool is None:
                tool_result_dict = {"success": False, "error": f"Tool '{tool_name}' not found"}
            else:
                result = tool.run(**args)
                tool_result_dict = result.model_dump()

            yield ObservationEvent(tool=tool_name, result=tool_result_dict)

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(tool_result_dict),
            })

    yield ErrorEvent(message=f"Reached max_steps ({max_steps}) without a final answer.")
