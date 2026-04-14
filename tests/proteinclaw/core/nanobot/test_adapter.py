import json
import pytest
from unittest.mock import MagicMock
from proteinclaw.core.nanobot.adapter import WebSocketAdapter
from nanobot.agent.hook import AgentHookContext


def make_ctx(**kwargs):
    ctx = AgentHookContext.__new__(AgentHookContext)
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    return ctx


@pytest.mark.asyncio
async def test_on_stream_emits_token_event():
    events = []

    async def send(e):
        events.append(e)

    adapter = WebSocketAdapter(send_json=send)
    ctx = make_ctx()
    await adapter.on_stream(ctx, "Hello")
    assert events == [{"type": "token", "content": "Hello"}]


@pytest.mark.asyncio
async def test_before_execute_tools_emits_tool_call():
    events = []

    async def send(e):
        events.append(e)

    adapter = WebSocketAdapter(send_json=send)
    tc = MagicMock()
    tc.name = "uniprot_search"
    tc.arguments = {"query": "BRCA1"}
    ctx = make_ctx(tool_calls=[tc])
    await adapter.before_execute_tools(ctx)
    assert events == [{"type": "tool_call", "tool": "uniprot_search", "args": {"query": "BRCA1"}}]


@pytest.mark.asyncio
async def test_after_iteration_emits_observation():
    events = []

    async def send(e):
        events.append(e)

    adapter = WebSocketAdapter(send_json=send)
    tc = MagicMock()
    tc.name = "uniprot_search"
    result_data = {"success": True, "data": "P38398"}
    ctx = make_ctx(
        tool_calls=[tc],
        tool_results=[json.dumps(result_data)],
    )
    await adapter.after_iteration(ctx)
    assert len(events) == 1
    assert events[0]["type"] == "observation"
    assert events[0]["tool"] == "uniprot_search"
    assert events[0]["result"]["success"] is True


def test_wants_streaming_returns_true():
    async def send(e): pass
    adapter = WebSocketAdapter(send_json=send)
    assert adapter.wants_streaming() is True
