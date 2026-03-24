import json
import pytest
from unittest.mock import patch, MagicMock
from proteinclaw.agent.loop import run_agent
from proteinbox.tools.registry import ProteinTool, ToolResult, TOOL_REGISTRY

class FakeUniProtTool(ProteinTool):
    name: str = "uniprot"
    description: str = "Fake UniProt"
    parameters: dict = {"type": "object", "properties": {"accession_id": {"type": "string"}}, "required": ["accession_id"]}
    def run(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"name": "TP53", "organism": "Homo sapiens"}, display="TP53 — Homo sapiens")

@pytest.fixture(autouse=True)
def patch_registry():
    with patch.dict(TOOL_REGISTRY, {"uniprot": FakeUniProtTool()}, clear=True):
        yield

def _make_tool_call_msg(tool_name: str, args: dict):
    tc = MagicMock()
    tc.id = "call_123"
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    return msg

def _make_final_msg(content: str):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    return msg

@pytest.mark.asyncio
async def test_agent_calls_tool_then_answers():
    events = []

    call_sequence = [
        _make_tool_call_msg("uniprot", {"accession_id": "P04637"}),
        _make_final_msg("P04637 is TP53 from Homo sapiens."),
    ]
    call_iter = iter(call_sequence)

    with patch("proteinclaw.agent.loop.call_llm", side_effect=lambda **kw: next(call_iter)):
        async for event in run_agent(
            message="What is P04637?",
            model="gpt-4o",
            history=[],
        ):
            events.append(event)

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    final_tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert "TP53" in final_tokens

@pytest.mark.asyncio
async def test_agent_respects_max_steps():
    # Always returns a tool call — should stop after max_steps
    def always_tool(**kw):
        return _make_tool_call_msg("uniprot", {"accession_id": "P04637"})

    events = []
    with patch("proteinclaw.agent.loop.call_llm", side_effect=always_tool):
        async for event in run_agent(
            message="loop forever",
            model="gpt-4o",
            history=[],
            max_steps=3,
        ):
            events.append(event)

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "max" in error_events[0]["message"].lower() or "step" in error_events[0]["message"].lower()
