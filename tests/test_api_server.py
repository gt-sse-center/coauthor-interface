import importlib
from unittest.mock import MagicMock, call, patch

import pytest

import coauthor_interface.backend.api_server as srv
from coauthor_interface.backend.api_server import app


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
    srv.SESSIONS.clear()
    srv.SESSIONS[session_id] = {
        "last_query_timestamp": 0,
        "current_action_in_progress": None,
        "parsed_actions": [],
        "intervention_on": False,
    }
    srv.examples = {0: ""}
    srv.blocklist = []

    logs = [
        {
            "eventName": "system-initialize",
            "eventSource": "api",
            "eventTimestamp": 1750449480896,
            "textDelta": "",
            "cursorRange": "",
            "currentDoc": "\n",
            "currentCursor": {},
            "currentSuggestions": [],
            "currentSuggestionIndex": 0,
            "currentHoverIndex": "",
            "currentN": "",
            "currentMaxToken": "",
            "currentTemperature": "",
            "currentTopP": "",
            "currentPresencePenalty": "",
            "currentFrequencyPenalty": "",
            "originalSuggestions": [],
        },
        {
            "eventName": "suggestion-get",
            "eventSource": "user",
            "eventTimestamp": 1750449482589,
            "textDelta": "",
            "cursorRange": "",
            "currentDoc": "",
            "currentCursor": {},
            "currentSuggestions": [],
            "currentSuggestionIndex": 0,
            "currentHoverIndex": "",
            "currentN": "5",
            "currentMaxToken": "50",
            "currentTemperature": "0.95",
            "currentTopP": "1",
            "currentPresencePenalty": "0.5",
            "currentFrequencyPenalty": "0.5",
            "originalSuggestions": [],
        },
    ]

    payload = {
        "session_id": session_id,
        "domain": "test",
        "example": 0,
        "example_text": "",
        "doc": "",
        "logs": logs,
        "n": 1,
        "max_tokens": 5,
        "temperature": 0.5,
        "top_p": 0.9,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stop": [],
        "engine": "gpt-3.5-turbo",
        "suggestions": [],
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["original_suggestions"] == []
    assert data["suggestions_with_probabilities"] == []


@patch("coauthor_interface.backend.api_server.read_access_codes")
@patch("coauthor_interface.backend.api_server.read_prompts")
@patch("coauthor_interface.backend.api_server.read_examples")
@patch("coauthor_interface.backend.api_server.append_session_to_file")  # Patch to prevent file writes
@patch("coauthor_interface.backend.api_server.print_current_sessions")
@patch("coauthor_interface.backend.api_server.print_verbose")
@patch("coauthor_interface.backend.api_server.gc.collect")  # Patch to avoid running garbage collection
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


@patch("coauthor_interface.backend.api_server.append_session_to_file")  # Patch to prevent file writes
@patch("coauthor_interface.backend.api_server.read_access_codes")
@patch("coauthor_interface.backend.api_server.read_prompts")
@patch("coauthor_interface.backend.api_server.read_examples")
@patch("coauthor_interface.backend.api_server.get_uuid")
@patch("coauthor_interface.backend.api_server.save_log_to_jsonl")
@patch("coauthor_interface.backend.api_server.print_current_sessions")
@patch("coauthor_interface.backend.api_server.print_verbose")
@patch("coauthor_interface.backend.api_server.gc.collect")
def test_multiple_sessions_do_not_mix_logs(
    mock_gc,
    mock_print_verbose,
    mock_print_current_sessions,
    mock_save_log_to_jsonl,
    mock_get_uuid,
    mock_read_examples,
    mock_read_prompts,
    mock_read_access_codes,
    mock_append_session_to_file,
    client,
):
    # Set up mocks for start_session
    mock_get_uuid.side_effect = ["sessionA", "sessionB"]
    mock_read_examples.return_value = {"example1": "Example A", "example2": "Example B"}
    mock_read_prompts.return_value = {"prompt1": "Prompt A", "prompt2": "Prompt B"}

    class DummyConfig:
        def __init__(self, prompt, example):
            self.prompt = prompt
            self.example = example
            self.engine = "gpt-test"
            self.domain = "test-domain"

        def convert_to_dict(self):
            return {"engine": self.engine, "domain": self.domain}

    mock_read_access_codes.return_value = {
        "codeA": DummyConfig("prompt1", "example1"),
        "codeB": DummyConfig("prompt2", "example2"),
    }

    # ----- Start two sessions -----
    response1 = client.post("/api/start_session", json={"accessCode": "codeA"})
    response2 = client.post("/api/start_session", json={"accessCode": "codeB"})

    session_id_1 = response1.get_json()["session_id"]
    session_id_2 = response2.get_json()["session_id"]

    # End both sessions with different logs
    logs_1 = [{"event": "keypress", "value": "A"}]
    logs_2 = [{"event": "click", "value": "B"}]

    client.post("/api/end_session", json={"sessionId": session_id_1, "logs": logs_1})
    client.post("/api/end_session", json={"sessionId": session_id_2, "logs": logs_2})

    # Check that logs were written to different files with correct content
    srv.proj_dir = "some_fake_proj_dir"
    expected_path_1 = f"{srv.proj_dir}/{session_id_1}.jsonl"
    expected_path_2 = f"{srv.proj_dir}/{session_id_2}.jsonl"

    # Check that save_log_to_jsonl called twice - once per session
    assert mock_save_log_to_jsonl.call_count == 2
    mock_save_log_to_jsonl.assert_has_calls(
        [
            call(expected_path_1, logs_1),
            call(expected_path_2, logs_2),
        ],
        any_order=True,
    )

    # Ensure logs weren't crossed
    actual_calls = mock_save_log_to_jsonl.call_args_list

    # checks that log content passed to save_log_to_jsonl for each session is different
    assert actual_calls[0][0][1] != actual_calls[1][0][1]


def test_query_invalid_session(client):
    """POST /api/query with an unknown session_id returns failure."""
    payload = {
        "session_id": "no_such_session",
        "domain": "test",
        "example": 0,
        "example_text": "",
        "doc": "",
        "logs": [],
        "n": 1,
        "max_tokens": 5,
        "temperature": 0.5,
        "top_p": 0.9,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stop": [],
        "engine": "gpt-3.5-turbo",
        "suggestions": [],
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] is False
    assert "not been established" in data["message"]


@patch("coauthor_interface.backend.api_server.retrieve_log_paths")
def test_get_log_invalid_session(mock_retrieve_paths, client):
    """POST /api/get_log with unknown session_id returns failure."""
    mock_retrieve_paths.return_value = {}
    # Ensure args.replay_dir exists for retrieve_log_paths
    srv.args = type("A", (), {"replay_dir": "ignored"})()

    response = client.post("/api/get_log", json={"sessionId": "unknown"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] is False
    # KeyError message will be the missing key name (as string repr)
    assert data["message"] == "'unknown'"


# --- Happy path tests ---
@patch("coauthor_interface.backend.api_server.OpenAI")  # Mock the OpenAI class
@patch("coauthor_interface.backend.api_server.parse_suggestion")
@patch("coauthor_interface.backend.api_server.parse_probability")
@patch("coauthor_interface.backend.api_server.filter_suggestions")
def test_query_success(
    mock_filter,
    mock_prob,
    mock_sugg,
    mock_openai_class,
    client,
):
    """POST /api/query returns parsed and filtered suggestions on success."""
    from types import SimpleNamespace

    # Ensure DEV_MODE is disabled for this test
    srv.DEV_MODE = False
    srv.verbose = False

    # Set the api_keys global variable
    srv.api_keys = {("openai", "default"): "fake-api-key"}

    # Arrange mocks
    session_id = "success-session"
    srv.SESSIONS.clear()
    srv.SESSIONS[session_id] = {
        "last_query_timestamp": 0,
        "current_action_in_progress": None,
        "parsed_actions": [],
        "intervention_on": False,
    }
    srv.examples = {0: "ex"}
    srv.blocklist = []

    # Set up the mock OpenAI client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Fake OpenAI response
    fake_choice = SimpleNamespace(
        text=" sug",
        logprobs={"token_logprobs": [0.1], "tokens": ["sug"]},
    )
    mock_response = SimpleNamespace(choices=[fake_choice])
    mock_client.completions.create.return_value = mock_response

    mock_sugg.return_value = " sug_mod"
    mock_prob.return_value = 0.42
    # filter_suggestions returns a list of tuples and counts
    mock_filter.return_value = ([(" sug_mod", 0.42, "engine")], {})

    logs = [
        {
            "eventName": "system-initialize",
            "eventSource": "api",
            "eventTimestamp": 1750449480896,
            "textDelta": "",
            "cursorRange": "",
            "currentDoc": "\n",
            "currentCursor": {},
            "currentSuggestions": [],
            "currentSuggestionIndex": 0,
            "currentHoverIndex": "",
            "currentN": "",
            "currentMaxToken": "",
            "currentTemperature": "",
            "currentTopP": "",
            "currentPresencePenalty": "",
            "currentFrequencyPenalty": "",
            "originalSuggestions": [],
        },
        {
            "eventName": "suggestion-get",
            "eventSource": "user",
            "eventTimestamp": 1750449482589,
            "textDelta": "",
            "cursorRange": "",
            "currentDoc": "",
            "currentCursor": {},
            "currentSuggestions": [],
            "currentSuggestionIndex": 0,
            "currentHoverIndex": "",
            "currentN": "5",
            "currentMaxToken": "50",
            "currentTemperature": "0.95",
            "currentTopP": "1",
            "currentPresencePenalty": "0.5",
            "currentFrequencyPenalty": "0.5",
            "originalSuggestions": [],
        },
    ]

    payload = {
        "session_id": session_id,
        "domain": "test",
        "example": 0,
        "example_text": "ex",
        "doc": "",
        "logs": logs,
        "n": 1,
        "max_tokens": 5,
        "temperature": 0.5,
        "top_p": 0.9,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stop": [],
        "engine": "engine",
        "suggestions": [],
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] is True
    # original_suggestions built from parse_suggestion & parse_probability
    assert data["original_suggestions"] == [
        {
            "original": " sug_mod",
            "trimmed": "sug_mod",
            "probability": 0.42,
            "source": "engine",
        }
    ]
    # suggestions_with_probabilities reflecting filter_suggestions
    assert data["suggestions_with_probabilities"] == [
        {
            "index": 0,
            "original": " sug_mod",
            "trimmed": "sug_mod",
            "probability": 0.42,
            "source": "engine",
        }
    ]
    # Control parameters returned
    assert data["ctrl"]["n"] == 1
    assert data["ctrl"]["max_tokens"] == 5


@patch("coauthor_interface.backend.api_server.retrieve_log_paths")
@patch("coauthor_interface.backend.api_server.read_log")
@patch("coauthor_interface.backend.api_server.compute_stats")
@patch("coauthor_interface.backend.api_server.get_last_text_from_log")
@patch("coauthor_interface.backend.api_server.get_config_for_log")
def test_get_log_success(
    mock_get_config,
    mock_last_text,
    mock_stats,
    mock_read_log,
    mock_retrieve,
    client,
):
    """POST /api/get_log returns logs and metadata on success."""
    session_id = "log-session"
    fake_path = "/fake/log.jsonl"
    fake_logs = [{"evt": 1}]
    fake_stats = {"count": 1}
    fake_last = "end"
    fake_conf = {"k": "v"}

    mock_retrieve.return_value = {session_id: fake_path}
    mock_read_log.return_value = fake_logs
    mock_stats.return_value = fake_stats
    mock_last_text.return_value = fake_last
    mock_get_config.return_value = fake_conf

    # Provide args and metadata for get_log
    srv.args = type("A", (), {"replay_dir": "ignored"})()
    srv.metadata = {}
    srv.metadata_path = "meta"

    response = client.post("/api/get_log", json={"sessionId": session_id})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] is True
    assert data["logs"] == fake_logs
    assert data["stats"] == fake_stats
    assert data["last_text"] == fake_last
    assert data["config"] == fake_conf
