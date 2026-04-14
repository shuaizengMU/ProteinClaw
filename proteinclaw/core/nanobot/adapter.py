"""WebSocketAdapter: translates nanobot AgentHook events to ProteinClaw WebSocket protocol.

Frontend expects these event types (unchanged from original protocol):
  {"type": "token",       "content": "<delta>"}
  {"type": "tool_call",   "tool": "<name>", "args": {...}}
  {"type": "observation", "tool": "<name>", "result": {...}}
  {"type": "done"}
  {"type": "error",       "message": "<msg>"}
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from nanobot.agent.hook import AgentHook, AgentHookContext


class WebSocketAdapter(AgentHook):
    """Bridges nanobot lifecycle events to the existing WebSocket event protocol."""

    def __init__(self, send_json: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        super().__init__()
        self._send = send_json

    def wants_streaming(self) -> bool:
        """Tell nanobot to stream tokens — required for token-by-token output."""
        return True

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        await self._send({"type": "token", "content": delta})

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        for tc in context.tool_calls:
            await self._send({
                "type": "tool_call",
                "tool": tc.name,
                "args": tc.arguments,
            })

    async def after_iteration(self, context: AgentHookContext) -> None:
        """Emit one observation event per tool result."""
        for tc, raw_result in zip(context.tool_calls, context.tool_results):
            if isinstance(raw_result, str):
                try:
                    result = json.loads(raw_result)
                except (json.JSONDecodeError, ValueError):
                    result = {"raw": raw_result}
            elif isinstance(raw_result, dict):
                result = raw_result
            else:
                result = {"raw": str(raw_result)}

            await self._send({
                "type": "observation",
                "tool": tc.name,
                "result": result,
            })
