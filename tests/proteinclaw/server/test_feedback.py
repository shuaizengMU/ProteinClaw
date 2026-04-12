from fastapi.testclient import TestClient
from proteinclaw.server.main import app

client = TestClient(app)


def test_feedback_positive_returns_ok():
    resp = client.post("/feedback", json={
        "feedback_type": "positive",
        "category": None,
        "comment": "Very helpful!",
        "message_content": "The protein folding prediction was accurate."
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_feedback_negative_returns_ok():
    resp = client.post("/feedback", json={
        "feedback_type": "negative",
        "category": "Not factually correct",
        "comment": "The citation was wrong.",
        "message_content": "According to Smith et al. 2020..."
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_feedback_missing_type_returns_422():
    resp = client.post("/feedback", json={
        "comment": "some comment",
        "message_content": "some content"
    })
    assert resp.status_code == 422


def test_feedback_invalid_type_returns_422():
    resp = client.post("/feedback", json={
        "feedback_type": "invalid_value",
        "comment": "test",
        "message_content": "test"
    })
    assert resp.status_code == 422
