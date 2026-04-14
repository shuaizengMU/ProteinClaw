import asyncio
import pytest
from unittest.mock import MagicMock
from proteinclaw.core.nanobot.tools import ProteinboxToolWrapper, build_tool_registry


def make_fake_tool(name="test_tool", result_data=None):
    """Create a mock ProteinTool."""
    tool = MagicMock()
    tool.name = name
    tool.description = "A test tool"
    tool.parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    result = MagicMock()
    result.model_dump.return_value = result_data or {"success": True, "data": "result"}
    tool.run.return_value = result
    return tool


def test_wrapper_name_and_description():
    fake = make_fake_tool(name="uniprot_search")
    wrapper = ProteinboxToolWrapper(fake)
    assert wrapper.name == "uniprot_search"
    assert wrapper.description == "A test tool"


def test_wrapper_parameters():
    fake = make_fake_tool()
    wrapper = ProteinboxToolWrapper(fake)
    assert wrapper.parameters["type"] == "object"
    assert "query" in wrapper.parameters["properties"]


@pytest.mark.asyncio
async def test_wrapper_execute_calls_run_in_thread():
    fake = make_fake_tool()
    wrapper = ProteinboxToolWrapper(fake)
    result = await wrapper.execute(query="BRCA1")
    fake.run.assert_called_once_with(query="BRCA1")
    import json
    parsed = json.loads(result)
    assert parsed["success"] is True
    assert parsed["data"] == "result"


def test_build_tool_registry_returns_registry():
    from nanobot.agent.tools.registry import ToolRegistry
    registry = build_tool_registry()
    assert isinstance(registry, ToolRegistry)
    assert len(registry) > 0
