import json
import os
import time
from pathlib import Path
from unittest.mock import patch
import pytest

from coauthor_interface.backend.helper import (
    append_session_to_file,
    apply_ops,
    compute_stats,
    get_config_for_log,
    get_text_and_mask,
    print_current_sessions,
    print_verbose,
    retrieve_log_paths,
    save_log_to_json,
    save_log_to_jsonl,
    check_for_level_3_actions,
)
from coauthor_interface.thought_toolkit.PluginInterface import (
    Plugin,
    Intervention,
    InterventionEnum,
)


def test_print_verbose(capsys):
    arg_dict = {"a": 1, "b": 2}
    print_verbose("Test Title", arg_dict, verbose=True)
    captured = capsys.readouterr()
    assert "Test Title" in captured.out
    assert "a: 1" in captured.out


def test_print_current_sessions(capsys):
    now = time.time()
    sessions = {
        "session1": {
            "start_timestamp": now - 60,
            "last_query_timestamp": now - 100,
        },
        "session2": {
            "start_timestamp": now - 120,
            "last_query_timestamp": now - 200,
        },
    }
    print_current_sessions(sessions, "Session Info")
    captured = capsys.readouterr()
    assert "Session Info" in captured.out
    assert "session1" in captured.out


def test_retrieve_log_paths(fs):
    fs.create_file("/logs/test.json")
    fs.create_file("/logs/test.jsonl")
    os.utime("/logs/test.jsonl", (time.time(), time.time() + 10))

    result = retrieve_log_paths(Path("/logs"))
    assert "test" in result
    assert result["test"].endswith(".jsonl")


def test_append_session_to_file(fs):
    path = Path("/logs/history.jsonl")
    fs.create_file(path)
    session = {"id": "abc"}
    append_session_to_file(session, path)
    content = path.read_text().strip()
    assert json.loads(content) == session


def test_save_log_to_json(fs):
    path = Path("/logs/log.json")
    fs.create_file(path)
    log = {"a": 1}
    save_log_to_json(path, log)
    with open(path) as f:
        assert json.load(f) == log


def test_save_log_to_jsonl(fs):
    path = Path("/logs/log.jsonl")
    fs.create_file(path)
    log = [{"a": 1}, {"b": 2}]
    save_log_to_jsonl(path, log)
    lines = path.read_text().strip().split("\n")
    assert [json.loads(line) for line in lines] == log


def test_compute_stats():
    log = [
        {"eventName": "insert"},
        {"eventName": "delete"},
        {"eventName": "insert"},
    ]
    stats = compute_stats(log)
    assert stats["eventCounter"] == {"insert": 2, "delete": 1}


def test_apply_ops():
    doc = "Hello"
    mask = "P" * len(doc)
    ops = [{"retain": 5}, {"insert": " world"}, {"delete": 3}]
    result_text, result_mask = apply_ops(doc, mask, ops, "api")
    assert result_text.endswith("wo")
    assert "A" in result_mask


def test_get_text_and_mask_remove_prompt():
    events = [
        {"currentDoc": "Prompt", "textDelta": {}},
        {
            "eventName": "edit",
            "eventSource": "user",
            "textDelta": {"ops": [{"retain": 6}, {"insert": " answer"}]},
        },
    ]
    text, mask = get_text_and_mask(events, 2)
    assert text.strip() == "answer"
    assert "U" in mask


def test_get_text_and_mask_keep_prompt():
    events = [
        {"currentDoc": "Prompt", "textDelta": {}},
        {
            "eventName": "edit",
            "eventSource": "api",
            "textDelta": {"ops": [{"retain": 6}, {"insert": " answer"}]},
        },
    ]
    text, mask = get_text_and_mask(events, 2, remove_prompt=False)
    assert text.startswith("Prompt")
    assert "P" in mask


def test_get_config_for_log(fs):
    session_id = "session123"
    metadata = {session_id: {"config": "abc"}}
    metadata_path = Path("/logs/meta.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata))

    def mock_update_metadata(metadata, path):
        return json.loads(path.read_text())

    with patch(
        "coauthor_interface.backend.helper.update_metadata",
        side_effect=mock_update_metadata,
    ):
        config = get_config_for_log(session_id, {}, metadata_path)
        assert config["config"] == "abc"


@pytest.fixture
def mock_plugin_1():
    class MockPlugin1(Plugin):
        def __init__(self):
            pass

        @staticmethod
        def get_plugin_name() -> str:
            return "mock_plugin_1"

        @staticmethod
        def detection_detected(action) -> bool:
            return action.get("level_3_action_type") == "insert_text"

        @staticmethod
        def intervention_action() -> Intervention:
            return Intervention(InterventionEnum.TOAST, "Mock plugin intervention")

    return MockPlugin1


@pytest.fixture
def mock_plugin_2():
    class MockPlugin2(Plugin):
        def __init__(self):
            pass

        @staticmethod
        def get_plugin_name() -> str:
            return "mock_plugin_2"

        @staticmethod
        def detection_detected(action) -> bool:
            return action.get("level_3_action_type") == "delete_text"

        @staticmethod
        def intervention_action() -> Intervention:
            return Intervention(InterventionEnum.TOAST, "Mock plugin 2 intervention")

    return MockPlugin2


@pytest.fixture
def mock_plugins(mock_plugin_1, mock_plugin_2):
    plugin1 = mock_plugin_1()
    plugin2 = mock_plugin_2()

    return [plugin1, plugin2]


def test_check_for_level_3_actions_when_n_actions_exceeds_list_length(mock_plugins):
    # Test case where n_actions (5) is longer than action_lst (2 items)
    actions = [
        {"level_3_action_type": "mock_plugin_1"},
        {"level_3_action_type": "mock_plugin_2"},
    ]
    result = check_for_level_3_actions(actions, mock_plugins, n_actions=5, pattern_count_threshold=2)
    assert result == []


def test_check_for_level_3_actions_when_multiple_plugins_meet_threshold(mock_plugins):
    # Test case with multiple plugins meeting threshold
    actions = [
        {"level_3_action_type": "mock_plugin_1"},
        {"level_3_action_type": "mock_plugin_1"},
        {"level_3_action_type": "mock_plugin_2"},
        {"level_3_action_type": "mock_plugin_1"},
        {"level_3_action_type": "random_action"},
        {"level_3_action_type": "mock_plugin_1"},
    ]
    result = check_for_level_3_actions(actions, mock_plugins, n_actions=6, pattern_count_threshold=3)

    assert len(result) == 1  # Only plugin 1 meets threshold
    assert {p.get_plugin_name() for p in result} == {"mock_plugin_1"}


def test_check_for_level_3_actions_when_no_plugins_meet_threshold(mock_plugins):
    # Test case where no plugins meet threshold
    actions = [
        {"level_3_action_type": "other_action"},
        {"level_3_action_type": "other_action"},
        {"level_3_action_type": "other_action"},
    ]
    result = check_for_level_3_actions(actions, mock_plugins, n_actions=3, pattern_count_threshold=2)
    assert len(result) == 0
