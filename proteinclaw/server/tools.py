from fastapi import APIRouter
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY

router = APIRouter()

# Discover all tools once at import time (populates TOOL_REGISTRY)
discover_tools()


@router.get("/tools")
def list_tools():
    return {
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in TOOL_REGISTRY.values()
        ]
    }
