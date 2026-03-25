import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from proteinclaw.server.main import app
from proteinclaw.core.agent.events import (
    TokenEvent, DoneEvent, ToolCallEvent, ObservationEvent, ErrorEvent
)


@pytest.mark.asyncio
async def test_get_tools():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_post_chat():
    async def mock_run(**kwargs):
        yield TokenEvent(content="Hello ")
        yield TokenEvent(content="world")
        yield DoneEvent()

    with patch("proteinclaw.server.chat.run", side_effect=mock_run):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={
                "message": "What is P04637?",
                "model": "gpt-4o",
                "history": [],
            })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "Hello" in data["reply"]


def test_websocket_chat():
    async def mock_run(**kwargs):
        yield ToolCallEvent(tool="uniprot", args={"accession_id": "P04637"})
        yield ObservationEvent(tool="uniprot", result={"success": True, "data": {"name": "TP53"}})
        yield TokenEvent(content="TP53 is ")
        yield TokenEvent(content="a tumor suppressor.")
        yield DoneEvent()

    with patch("proteinclaw.server.chat.run", side_effect=mock_run):
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({
                "message": "What is P04637?",
                "model": "gpt-4o",
                "history": [],
            })
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if event["type"] in ("done", "error"):
                    break

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    assert "done" in types
