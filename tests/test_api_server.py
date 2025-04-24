import importlib
import pytest
from src.coauthor_interface.backend.api_server import app
import src.coauthor_interface.backend.api_server as srv

@pytest.fixture
def client():
    """Flask test client."""
    return app.test_client()


def test_query_dev_mode_returns_empty(client, monkeypatch):
    """When DEV_MODE=true, /api/query should return empty suggestions."""
    # Enable DEV_MODE
    monkeypatch.setenv("DEV_MODE", "true")
    # Needs to re load the module to update DEV_MODE
    importlib.reload(srv)
    
    srv.verbose = False

    # Prepare session and minimal globals
    session_id = "test-session-2"
    srv.SESSIONS[session_id] = {"last_query_timestamp": 0}
    srv.examples = {0: ""}
    srv.blocklist = []

    payload = {
        "session_id": session_id,
        "example": 0,
        "doc": "",
        "suggestions": [],
        "n": 1,
        "max_tokens": 5,
        "temperature": 0.5,
        "top_p": 0.9,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stop": [],
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["original_suggestions"] == []
    assert data["suggestions_with_probabilities"] == []
