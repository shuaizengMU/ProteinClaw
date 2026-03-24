from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel

TOOL_REGISTRY: dict[str, "ProteinTool"] = {}


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    display: Optional[str] = None
    error: Optional[str] = None


class ProteinTool(BaseModel):
    name: str
    description: str
    parameters: dict  # OpenAI function-calling compatible JSON Schema

    model_config = {"arbitrary_types_allowed": True}

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError


def register_tool(cls: type[ProteinTool]) -> type[ProteinTool]:
    """Class decorator that instantiates and registers a ProteinTool."""
    instance = cls()
    TOOL_REGISTRY[instance.name] = instance
    return cls


def discover_tools() -> dict[str, ProteinTool]:
    """Import all modules in proteinbox/tools/ to trigger @register_tool decorators."""
    import pkgutil
    import importlib
    import proteinbox.tools as pkg
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        if module_name != "registry":
            importlib.import_module(f"proteinbox.tools.{module_name}")
    return TOOL_REGISTRY
