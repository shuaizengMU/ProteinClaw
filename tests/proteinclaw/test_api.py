import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from proteinclaw.main import app

@pytest.mark.asyncio
async def test_get_tools():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)

@pytest.mark.asyncio
async def test_post_chat():
    async def mock_agent(**kwargs):
        yield {"type": "token", "content": "Hello "}
        yield {"type": "token", "content": "world"}
        yield {"type": "done"}

    with patch("proteinclaw.api.chat.run_agent", side_effect=mock_agent):
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
