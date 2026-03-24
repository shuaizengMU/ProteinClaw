from proteinbox.tools.registry import ProteinTool, ToolResult
from proteinclaw.agent.prompt import build_system_prompt


class FakeTool(ProteinTool):
    name: str = "fake_tool"
    description: str = "Does something fake"
    parameters: dict = {}

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data=None)


def test_build_system_prompt_contains_tool_name():
    prompt = build_system_prompt({"fake_tool": FakeTool()})
    assert "fake_tool" in prompt


def test_build_system_prompt_contains_tool_description():
    prompt = build_system_prompt({"fake_tool": FakeTool()})
    assert "Does something fake" in prompt


def test_build_system_prompt_empty_tools():
    prompt = build_system_prompt({})
    assert isinstance(prompt, str)
    assert len(prompt) > 0
