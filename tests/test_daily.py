import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_daily_returns_200():
    response = client.get("/daily")
    assert response.status_code == 200

def test_daily_has_7_blocks():
    response = client.get("/daily")
    data = response.json()
    assert len(data["blocks"]) == 7

def test_each_block_has_required_fields():
    response = client.get("/daily")
    data = response.json()
    for block in data["blocks"]:
        assert "name" in block
        assert "instruction" in block
        assert "duration_seconds" in block

def test_session_has_title_and_closing():
    response = client.get("/daily")
    data = response.json()
    assert "session_title" in data
    assert "closing" in data
