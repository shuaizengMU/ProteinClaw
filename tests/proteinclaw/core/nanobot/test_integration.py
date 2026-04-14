"""Smoke test: verify the full nanobot stack wires up without errors.

Uses a mock provider so no real API key is required.
"""
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proteinclaw.core.nanobot.instance import set_workspace, get_nanobot, _instances
from proteinclaw.core.nanobot.adapter import WebSocketAdapter


@pytest.fixture(autouse=True)
def clean_instances():
    """Clear the instance cache between tests."""
    _instances.clear()
    yield
    _instances.clear()


def test_get_nanobot_returns_instance():
    with tempfile.TemporaryDirectory() as tmp:
        set_workspace(Path(tmp))
        import os
        os.environ.setdefault("OPENAI_API_KEY", "test-key-for-smoke")
        bot = get_nanobot("gpt-4o")
        from nanobot import Nanobot
        assert isinstance(bot, Nanobot)
        # proteinbox tools are registered (> 30), not nanobot builtins
        tool_names = bot._loop.tools.tool_names
        assert len(tool_names) > 30
        # nanobot built-ins are removed
        assert "read_file" not in tool_names
        assert "exec" not in tool_names


def test_adapter_emits_token_events():
    """Test that WebSocketAdapter.on_stream emits token events."""
    events = []

    async def collect(e):
        events.append(e)

    async def run():
        adapter = WebSocketAdapter(send_json=collect)
        from nanobot.agent.hook import AgentHookContext
        ctx = AgentHookContext.__new__(AgentHookContext)
        await adapter.on_stream(ctx, "Hello")
        await adapter.on_stream(ctx, " world")
        return events

    result = asyncio.run(run())
    assert result[0] == {"type": "token", "content": "Hello"}
    assert result[1] == {"type": "token", "content": " world"}


def test_get_nanobot_caches_instance():
    """Same model returns same instance."""
    with tempfile.TemporaryDirectory() as tmp:
        set_workspace(Path(tmp))
        import os
        os.environ.setdefault("OPENAI_API_KEY", "test-key-for-smoke")
        bot1 = get_nanobot("gpt-4o")
        bot2 = get_nanobot("gpt-4o")
        assert bot1 is bot2
