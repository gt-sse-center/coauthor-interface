import importlib
import pytest
from unittest.mock import patch, MagicMock
from coauthor_interface.backend.api_server import app
import coauthor_interface.backend.api_server as srv


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
    srv.SESSIONS.clear()  # clear since SESSIONS is a global variable
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


@patch("coauthor_interface.backend.api_server.read_access_codes")
@patch("coauthor_interface.backend.api_server.read_prompts")
@patch("coauthor_interface.backend.api_server.read_examples")
@patch(
    "coauthor_interface.backend.api_server.append_session_to_file"
)  # Patch to prevent file writes
@patch("coauthor_interface.backend.api_server.print_current_sessions")
@patch("coauthor_interface.backend.api_server.print_verbose")
@patch(
    "coauthor_interface.backend.api_server.gc.collect"
)  # Patch to avoid running garbage collection
def test_start_session_success(
    mock_gc,
    mock_print_verbose,
    mock_print_current_sessions,
    mock_append_session_to_file,
    mock_read_examples,
    mock_read_prompts,
    mock_read_access_codes,
    client,
):
    """Test that the start_session route returns the appropriate response"""

    # Arrange: Mock data
    mock_read_examples.return_value = {"example_1": "This is an example text."}
    mock_read_prompts.return_value = {"prompt_1": "This is a prompt text."}
    MockConfig = MagicMock()
    MockConfig.example = "example_1"
    MockConfig.prompt = "prompt_1"
    MockConfig.convert_to_dict.return_value = {"engine": "gpt-4", "domain": "general"}
    mock_read_access_codes.return_value = {"valid_access_code": MockConfig}

    srv.config_dir = "some_dir"
    srv.prompts = ["some prompt"]
    srv.metadata_path = "some_path"

    payload = {"domain": "general", "accessCode": "valid_access_code"}

    # get response
    response = client.post("/api/start_session", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"]
    assert data["access_code"] == "valid_access_code"
    assert data["example_text"] == "This is an example text."
    assert data["prompt_text"] == "This is a prompt text."
    assert data["engine"] == "gpt-4"
    assert data["domain"] == "general"
    assert "session_id" in data
    assert "example_text" in data
    assert "prompt_text" in data


@patch("coauthor_interface.backend.api_server.read_access_codes")
@patch("coauthor_interface.backend.api_server.read_prompts")
@patch("coauthor_interface.backend.api_server.read_examples")
@patch("coauthor_interface.backend.api_server.print_current_sessions")
def test_start_session_no_access_code_provided(
    mock_print_current_sessions,
    mock_read_examples,
    mock_read_prompts,
    mock_read_access_codes,
    client,
):
    # Arrange: mock data
    mock_read_access_codes.return_value = {"valid_access_code": MagicMock()}

    payload = {"accessCode": ""}  # Simulate missing or empty access code

    response = client.post("/api/start_session", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert not data["status"]
    assert "Invalid access code: (not provided)" in data["message"]


@patch("coauthor_interface.backend.api_server.save_log_to_jsonl")
@patch("coauthor_interface.backend.api_server.print_verbose")
@patch("coauthor_interface.backend.api_server.print_current_sessions")
@patch("coauthor_interface.backend.api_server.gc.collect")
def test_end_session_success(
    mock_gc,
    mock_print_current_sessions,
    mock_print_verbose,
    mock_save_log_to_jsonl,
    client,
):
    # Arrange: mock data
    session_id = "abc123"
    fake_log = [{"event": "key_press", "value": "a"}]
    srv.proj_dir = "some_fake_proj_dir"

    # Clear (since SESSIONS is a global variable) and populate SESSIONS with a fake session
    srv.SESSIONS.clear()
    srv.SESSIONS[session_id] = {
        "verification_code": "abc123",
    }

    payload = {
        "sessionId": session_id,
        "logs": fake_log,
    }

    response = client.post("/api/end_session", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"]
    assert "path" in data
    assert data["verification_code"] == "abc123"


@patch("coauthor_interface.backend.api_server.save_log_to_jsonl")
@patch("coauthor_interface.backend.api_server.print_verbose")
@patch("coauthor_interface.backend.api_server.print_current_sessions")
@patch("coauthor_interface.backend.api_server.gc.collect")
def test_end_session_save_log_failure(
    mock_gc,
    mock_print_current_sessions,
    mock_print_verbose,
    mock_save_log_to_jsonl,
    client,
):
    # Arrange mock data
    session_id = "def456"
    fake_log = [{"event": "click", "value": "submit"}]

    # Clear (since SESSIONS is a global variable) and populate SESSIONS with a fake session
    srv.SESSIONS.clear()
    srv.SESSIONS[session_id] = {
        "verification_code": "def456",
    }

    mock_save_log_to_jsonl.side_effect = Exception("Invalid filepath")

    payload = {
        "sessionId": session_id,
        "logs": fake_log,
    }

    response = client.post("/api/end_session", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert not data["status"]
    assert "Invalid filepath" in data["message"]
    assert data["verification_code"] == "def456"


@patch("coauthor_interface.backend.api_server.save_log_to_jsonl")
@patch("coauthor_interface.backend.api_server.print_verbose")
@patch("coauthor_interface.backend.api_server.print_current_sessions")
@patch("coauthor_interface.backend.api_server.gc.collect")
def test_end_session_missing_session(
    mock_gc,
    mock_print_current_sessions,
    mock_print_verbose,
    mock_save_log_to_jsonl,
    client,
):
    # Arrange mock data
    session_id = "nonexistent"
    fake_log = [{"event": "click", "value": "cancel"}]
    srv.proj_dir = "some_fake_proj_dir"

    payload = {
        "sessionId": session_id,
        "logs": fake_log,
    }

    response = client.post("/api/end_session", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"]  # Still true if log save works
    assert data["verification_code"] == "SERVER_ERROR"
