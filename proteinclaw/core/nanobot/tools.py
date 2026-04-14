"""Wraps all proteinbox tools as nanobot Tool subclasses."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.registry import ToolRegistry

from proteinbox.tools.registry import discover_tools


class ProteinboxToolWrapper(Tool):
    """Adapts a synchronous ProteinTool to nanobot's async Tool interface.

    Uses asyncio.to_thread so the sync tool.run() doesn't block the event loop.
    """

    def __init__(self, protein_tool: Any) -> None:
        self._tool = protein_tool

    @property
    def name(self) -> str:
        return self._tool.name

    @property
    def description(self) -> str:
        return self._tool.description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._tool.parameters

    async def execute(self, **kwargs: Any) -> str:
        result = await asyncio.to_thread(self._tool.run, **kwargs)
        return json.dumps(result.model_dump())


def build_tool_registry() -> ToolRegistry:
    """Auto-discover all proteinbox tools and wrap them into a ToolRegistry."""
    registry = ToolRegistry()
    for tool in discover_tools().values():
        registry.register(ProteinboxToolWrapper(tool))
    return registry
