# tests/proteinbox/test_registry.py
from proteinbox.tools.registry import (
    ToolResult, ProteinTool, register_tool, discover_tools, TOOL_REGISTRY
)

def test_tool_result_success():
    r = ToolResult(success=True, data={"key": "value"}, display="ok")
    assert r.success is True
    assert r.data == {"key": "value"}
    assert r.error is None

def test_tool_result_failure():
    r = ToolResult(success=False, data=None, error="something went wrong")
    assert r.success is False
    assert r.error == "something went wrong"

def test_register_tool_adds_to_registry():
    from unittest.mock import patch
    with patch.dict(TOOL_REGISTRY, {}, clear=False):
        @register_tool
        class DummyTool(ProteinTool):
            name: str = "dummy_isolated"
            description: str = "A dummy tool"
            parameters: dict = {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            }
            def run(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data={"x": kwargs["x"]}, display=kwargs["x"])

        assert "dummy_isolated" in TOOL_REGISTRY
        tool = TOOL_REGISTRY["dummy_isolated"]
        result = tool.run(x="hello")
        assert result.success is True
        assert result.data == {"x": "hello"}
    # After exiting context, dummy_isolated is removed from TOOL_REGISTRY

def test_protein_tool_run_raises_not_implemented():
    class BadTool(ProteinTool):
        name: str = "bad"
        description: str = "bad"
        parameters: dict = {}
    t = BadTool()
    import pytest
    with pytest.raises(NotImplementedError):
        t.run()
