"""Tests for VR chat API endpoint"""

import pytest
from fastapi.testclient import TestClient
from vrsecretary_gateway.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mode" in data


def test_vr_chat_missing_fields():
    """Test VR chat with missing required fields"""
    response = client.post("/api/vr_chat", json={})
    assert response.status_code == 422  # Validation error


def test_vr_chat_empty_text():
    """Test VR chat with empty user text"""
    response = client.post("/api/vr_chat", json={
        "session_id": "test-123",
        "user_text": "",
    })
    assert response.status_code == 422  # Validation error


# Note: Full integration tests require Ollama/Chatterbox running
# Add mocked tests for unit testing without external services
