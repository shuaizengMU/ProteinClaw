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
    """Import all modules in proteinbox/tools/ and proteinbox/api_tools/ to trigger @register_tool decorators."""
    import pkgutil
    import importlib
    import proteinbox.tools as tools_pkg
    for _, module_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
        if module_name != "registry":
            importlib.import_module(f"proteinbox.tools.{module_name}")

    try:
        import proteinbox.api_tools as api_pkg
        for _, module_name, _ in pkgutil.iter_modules(api_pkg.__path__):
            importlib.import_module(f"proteinbox.api_tools.{module_name}")
    except ImportError:
        pass

    try:
        import proteinbox.api_literature as lit_pkg
        for _, module_name, _ in pkgutil.iter_modules(lit_pkg.__path__):
            importlib.import_module(f"proteinbox.api_literature.{module_name}")
    except ImportError:
        pass

    return TOOL_REGISTRY
