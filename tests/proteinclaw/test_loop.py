import json
import pytest
from unittest.mock import patch
from proteinclaw.core.agent.loop import run
from proteinclaw.core.agent.events import (
    ToolCallEvent, ObservationEvent, TokenEvent, DoneEvent, ErrorEvent
)
from proteinbox.tools.registry import ProteinTool, ToolResult, TOOL_REGISTRY


class FakeUniProtTool(ProteinTool):
    name: str = "uniprot"
    description: str = "Fake UniProt"
    parameters: dict = {
        "type": "object",
        "properties": {"accession_id": {"type": "string"}},
        "required": ["accession_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            data={"name": "TP53", "organism": "Homo sapiens"},
            display="TP53 — Homo sapiens",
        )


@pytest.fixture(autouse=True)
def patch_registry():
    with patch.dict(TOOL_REGISTRY, {"uniprot": FakeUniProtTool()}, clear=True):
        yield


# ── Async generator helpers ───────────────────────────────────────────────────

async def _tool_call_gen(**kw):
    yield ("tool_calls", [{"id": "call_123", "name": "uniprot", "arguments": json.dumps({"accession_id": "P04637"})}])


async def _final_answer_gen(**kw):
    yield ("token", "P04637 is TP53 from Homo sapiens.")


async def _always_tool_gen(**kw):
    yield ("tool_calls", [{"id": "call_123", "name": "uniprot", "arguments": json.dumps({"accession_id": "P04637"})}])


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_calls_tool_then_answers():
    events = []

    call_sequence = [_tool_call_gen, _final_answer_gen]
    call_iter = iter(call_sequence)

    with patch("proteinclaw.core.agent.loop.call_llm_async_stream",
               side_effect=lambda **kw: next(call_iter)(**kw)):
        async for event in run(
            query="What is P04637?",
            history=[],
            model="gpt-4o",
        ):
            events.append(event)

    types = [e.type for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    final_tokens = "".join(e.content for e in events if isinstance(e, TokenEvent))
    assert "TP53" in final_tokens


@pytest.mark.asyncio
async def test_agent_respects_max_steps():
    events = []
    with patch("proteinclaw.core.agent.loop.call_llm_async_stream",
               side_effect=lambda **kw: _always_tool_gen(**kw)):
        async for event in run(
            query="loop forever",
            history=[],
            model="gpt-4o",
            max_steps=3,
        ):
            events.append(event)

    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(error_events) == 1
    assert "max" in error_events[0].message.lower() or "step" in error_events[0].message.lower()
