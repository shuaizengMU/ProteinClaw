import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from proteinclaw.server.main import app
from nanobot.nanobot import RunResult


def _make_mock_bot(content="Hello world"):
    """Return a mock Nanobot whose run() returns a RunResult with the given content."""
    mock_bot = MagicMock()
    mock_bot.run = AsyncMock(
        return_value=RunResult(content=content, tools_used=[], messages=[])
    )
    return mock_bot


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
    mock_bot = _make_mock_bot(content="Hello world")

    with patch("proteinclaw.server.chat.get_nanobot", return_value=mock_bot):
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
    mock_bot = _make_mock_bot(content="TP53 is a tumor suppressor.")

    with patch("proteinclaw.server.chat.get_nanobot", return_value=mock_bot):
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
    assert "done" in types
