from __future__ import annotations
import json
from typing import AsyncIterator
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY
from proteinclaw.agent.llm import call_llm, call_llm_stream, build_tools_schema
from proteinclaw.agent.prompt import build_system_prompt


async def run_agent(
    message: str,
    model: str,
    history: list[dict],
    max_steps: int = 10,
) -> AsyncIterator[dict]:
    """
    Run the ReAct agent loop. Yields WebSocket event dicts:
      {"type": "thinking",    "content": str}
      {"type": "tool_call",   "tool": str, "args": dict}
      {"type": "observation", "tool": str, "result": dict}
      {"type": "token",       "content": str}
      {"type": "done"}
      {"type": "error",       "message": str}
    """
    tools = discover_tools()
    tools_schema = build_tools_schema(tools)
    system_prompt = build_system_prompt(tools)

    messages: list[dict] = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": message}]
    )

    for step in range(max_steps):
        response_msg = call_llm(model=model, messages=messages, tools=tools_schema)

        # Tool call branch
        if response_msg.tool_calls:
            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response_msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
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

                yield {"type": "tool_call", "tool": tool_name, "args": args}

                tool = tools.get(tool_name)
                if tool is None:
                    tool_result_dict = {"success": False, "error": f"Tool '{tool_name}' not found"}
                else:
                    result = tool.run(**args)
                    tool_result_dict = result.model_dump()

                yield {"type": "observation", "tool": tool_name, "result": tool_result_dict}

                # Append tool result as tool message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result_dict),
                })

        # Final answer branch — stream the response
        else:
            final_content = response_msg.content or ""
            # Yield content as tokens (split by word for streaming feel if not using stream=True)
            for token in final_content.split(" "):
                yield {"type": "token", "content": token + " "}
            yield {"type": "done"}
            return

    # Exceeded max_steps
    yield {"type": "error", "message": f"Reached max_steps ({max_steps}) without a final answer."}
