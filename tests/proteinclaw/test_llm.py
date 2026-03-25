import pytest
from unittest.mock import patch, MagicMock
from proteinclaw.core.agent.llm import call_llm, call_llm_stream, build_tools_schema
from proteinbox.tools.registry import ProteinTool, ToolResult


class EchoTool(ProteinTool):
    name: str = "echo"
    description: str = "Echo back the input"
    parameters: dict = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }
    def run(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"text": kwargs["text"]}, display=kwargs["text"])


def test_build_tools_schema():
    tools = {"echo": EchoTool()}
    schema = build_tools_schema(tools)
    assert len(schema) == 1
    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "echo"
    assert "parameters" in schema[0]["function"]


def test_call_llm_returns_message():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello"
    mock_response.choices[0].message.tool_calls = None

    with patch("proteinclaw.core.agent.llm.litellm.completion", return_value=mock_response):
        msg = call_llm(
            model="gpt-4o",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )
    assert msg.content == "Hello"
    assert msg.tool_calls is None


def test_call_llm_with_tool_call():
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "echo"
    mock_tool_call.function.arguments = '{"text": "hello"}'

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tool_call]

    with patch("proteinclaw.core.agent.llm.litellm.completion", return_value=mock_response):
        msg = call_llm(
            model="gpt-4o",
            messages=[{"role": "user", "content": "echo hello"}],
            tools=[],
        )
    assert msg.tool_calls is not None
    assert msg.tool_calls[0].function.name == "echo"
