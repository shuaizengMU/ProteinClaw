import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from proteinclaw.server.main import app


@pytest.mark.asyncio
async def test_get_case_studies_returns_default_when_no_user_file(tmp_path):
    """When ~/.config/proteinclaw/case-studies.json doesn't exist, returns bundled defaults."""
    user_file = tmp_path / "case-studies.json"
    with patch("proteinclaw.server.case_studies.USER_CASE_STUDIES_PATH", user_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/case-studies")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert len(data["cases"]) > 0
    case = data["cases"][0]
    assert "id" in case
    assert "title" in case
    assert "category" in case
    assert "icon" in case
    assert "description" in case
    assert "examplePrompt" in case
    assert "exampleResult" in case


@pytest.mark.asyncio
async def test_get_case_studies_copies_default_to_user_path(tmp_path):
    """On first call, the default JSON is copied to the user config path."""
    user_file = tmp_path / "case-studies.json"
    assert not user_file.exists()
    with patch("proteinclaw.server.case_studies.USER_CASE_STUDIES_PATH", user_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/api/case-studies")
    assert user_file.exists()
    data = json.loads(user_file.read_text())
    assert "cases" in data


@pytest.mark.asyncio
async def test_get_case_studies_reads_user_file_when_present(tmp_path):
    """When the user file exists, its content is returned (allows customisation)."""
    user_file = tmp_path / "case-studies.json"
    custom = {"cases": [{"id": "custom", "title": "Custom Case", "category": "sequence",
                         "icon": "dna", "description": "desc", "examplePrompt": "prompt",
                         "exampleResult": "result"}]}
    user_file.write_text(json.dumps(custom))
    with patch("proteinclaw.server.case_studies.USER_CASE_STUDIES_PATH", user_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/case-studies")
    assert response.status_code == 200
    data = response.json()
    assert data["cases"][0]["id"] == "custom"


@pytest.mark.asyncio
async def test_get_case_studies_returns_500_on_corrupt_file(tmp_path):
    """When the case studies file is corrupt JSON, returns 500."""
    user_file = tmp_path / "case-studies.json"
    user_file.write_text("not valid json")
    with patch("proteinclaw.server.case_studies.USER_CASE_STUDIES_PATH", user_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/case-studies")
    assert response.status_code == 500
