from __future__ import annotations
import json
from typing import AsyncGenerator
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY
from proteinclaw.core.agent.llm import call_llm, build_tools_schema
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
        response_msg = call_llm(model=model, messages=messages, tools=tools_schema)

        if response_msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": response_msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response_msg.tool_calls
                ],
            })

            for tc in response_msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
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
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result_dict),
                })

        else:
            final_content = response_msg.content or ""
            for token in final_content.split(" "):
                yield TokenEvent(content=token + " ")
            yield DoneEvent()
            return

    yield ErrorEvent(message=f"Reached max_steps ({max_steps}) without a final answer.")
