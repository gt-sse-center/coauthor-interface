import json
from pathlib import Path
import pytest
from coauthor_interface.thought_toolkit.parse_all_consolidated import (
    parse_level_1_actions,
    parse_level_2_actions_from_level_1,
    parse_level_3_actions_from_level_2,
    populate_priority_list,
    action_type_priority_sort,
    process_logs,
)
from coauthor_interface.thought_toolkit.PluginInterface import (
    Plugin,
    Intervention,
    InterventionEnum,
)


@pytest.fixture
def raw_keylogs_from_frontend():
    """Fixture providing test keylogs data."""
    return {
        "session1": [
            {
                "eventName": "text-insert",
                "eventSource": "user",
                "eventTimestamp": 1629357370478,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "test"}]},
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 4,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 1,
            }
        ],
        "session2": [
            {
                "eventName": "text-insert",
                "eventSource": "user",
                "eventTimestamp": 1629357370478,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "test"}]},
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 4,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 1,
            },
            {
                "eventName": "text-insert",
                "eventSource": "user",
                "eventTimestamp": 1629357370478,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "test"}]},
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 4,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 1,
            },
        ],
    }


@pytest.fixture
def mock_plugin():
    """Fixture providing a mock plugin for testing."""

    class MockPlugin(Plugin):
        @staticmethod
        def get_plugin_name() -> str:
            return "mock_plugin"

        @staticmethod
        def detection_detected(action) -> bool:
            return action.get("level_1_action_type") == "insert_text"

        @staticmethod
        def intervention_action() -> Intervention:
            return Intervention(InterventionEnum.TOAST, "Mock plugin detected")

    return MockPlugin()


@pytest.fixture
def mock_plugin2():
    """Fixture providing another mock plugin for testing."""

    class MockPlugin2(Plugin):
        @staticmethod
        def get_plugin_name() -> str:
            return "mock_plugin2"

        @staticmethod
        def detection_detected(action) -> bool:
            return action.get("level_1_action_type") == "delete_text"

        @staticmethod
        def intervention_action() -> Intervention:
            return Intervention(InterventionEnum.TOAST, "Mock plugin 2 detected")

    return MockPlugin2()


@pytest.fixture
def fake_output_dir(fs):
    """Fixture providing a fake output directory."""
    output_dir = Path("/fake/output")
    fs.create_dir(output_dir)
    return output_dir


def test_parse_level_1_actions(raw_keylogs_from_frontend):
    """Test level 1 action parsing from raw keylogs."""
    result = parse_level_1_actions(raw_keylogs_from_frontend)

    # Check that all sessions are present
    assert set(result.keys()) == {"session1", "session2"}

    # Check that level_1_action_type is added
    for session_actions in result.values():
        for action in session_actions:
            assert "level_1_action_type" in action
            assert action["level_1_action_type"] == action["action_type"]


def test_parse_level_2_actions_from_level_1(raw_keylogs_from_frontend):
    """Test level 2 action parsing from level 1 actions."""
    level_1_actions = parse_level_1_actions(raw_keylogs_from_frontend)
    result = parse_level_2_actions_from_level_1(level_1_actions)

    # Check that all sessions are present
    assert set(result.keys()) == {"session1", "session2"}


def test_parse_level_3_actions_from_level_2(raw_keylogs_from_frontend):
    """Test level 3 action parsing from level 2 actions."""
    level_1_actions = parse_level_1_actions(raw_keylogs_from_frontend)
    level_2_actions = parse_level_2_actions_from_level_1(level_1_actions)
    result = parse_level_3_actions_from_level_2(level_2_actions)

    # Check that all sessions are present
    assert set(result.keys()) == {"session1", "session2"}


@pytest.fixture
def sample_actions():
    """Fixture providing sample actions for testing priority list population."""
    return {
        "session1": [
            {
                "level_1_action_type": "insert",
                "level_2_action_type": "major_insert",
                "level_3_action_type": "major_insert_major_semantic_diff",
            },
            {
                "level_1_action_type": "delete",
                "level_2_action_type": "minor_delete",
                "level_3_action_type": "minor_delete_minor_semantic_diff",
            },
        ],
        "session2": [
            {
                "level_1_action_type": "insert",
                "level_2_action_type": "minor_insert",
                "level_3_action_type": "minor_insert_mindless_edit",
            }
        ],
    }


def test_populate_priority_list(sample_actions):
    """Test priority list population from sample actions."""
    # Test with level_1_action_type
    level_1_priority_list = populate_priority_list(sample_actions, "level_1_action_type")
    assert isinstance(level_1_priority_list, list)
    assert set(level_1_priority_list) == {"insert", "delete"}

    # Test with level_2_action_type
    level_2_priority_list = populate_priority_list(sample_actions, "level_2_action_type")
    assert isinstance(level_2_priority_list, list)
    assert set(level_2_priority_list) == {
        "major_insert",
        "minor_delete",
        "minor_insert",
    }

    # Test with level_3_action_type
    level_3_priority_list = populate_priority_list(sample_actions, "level_3_action_type")
    assert isinstance(level_3_priority_list, list)
    assert set(level_3_priority_list) == {
        "major_insert_major_semantic_diff",
        "minor_delete_minor_semantic_diff",
        "minor_insert_mindless_edit",
    }


def test_action_type_priority_sort(raw_keylogs_from_frontend):
    """Test action type priority sorting of processed keylogs."""
    level_1_actions = parse_level_1_actions(raw_keylogs_from_frontend)
    level_2_actions = parse_level_2_actions_from_level_1(level_1_actions)
    level_3_actions = parse_level_3_actions_from_level_2(level_2_actions)

    priority_list = ["minor_insert_mindless_edit", "major_insert_major_semantic_diff"]
    result = action_type_priority_sort(priority_list, level_3_actions)

    # Check that all sessions are present
    assert set(result.keys()) == {"session1", "session2"}

    # Check that action_type is set based on priority
    for session_actions in result.values():
        for action in session_actions:
            assert "action_type" in action
            # Don't assume specific action types, just verify it's a string
            assert isinstance(action["action_type"], str)


@pytest.fixture
def test_logs_file(raw_keylogs_from_frontend, fs):
    """Fixture providing a test logs file with raw_keylogs_from_frontend data."""
    test_file = Path("/fake/input/test_logs.json")
    fs.create_file(test_file, contents=json.dumps(raw_keylogs_from_frontend))
    return test_file


def test_process_logs(test_logs_file, fs, fake_output_dir):
    """Test the complete processing pipeline of raw keylogs using fake filesystem."""
    # Process the keylogs
    process_logs(test_logs_file, fake_output_dir)

    # Check that all output files are created
    expected_files = [
        "level_1_actions_per_session.json",
        "level_2_actions_per_session.json",
        "level_3_actions_per_session.json",
        "action_type_with_priority_per_session.json",
    ]

    for filename in expected_files:
        output_file = fake_output_dir / filename
        assert output_file.exists()

        # Verify file contains valid JSON
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert len(data) > 0


def test_process_logs_nonexistent_input(fs, fake_output_dir):
    """Test processing with nonexistent raw keylogs file."""
    input_file = Path("/fake/input/nonexistent_keylogs.json")

    with pytest.raises(FileNotFoundError):
        process_logs(input_file, fake_output_dir)


def test_process_logs_invalid_json(fs, fake_output_dir):
    """Test processing with invalid raw keylogs JSON input."""
    input_file = Path("/fake/input/invalid_keylogs.json")

    # Create a file with invalid JSON
    fs.create_file(input_file, contents="invalid json content")

    with pytest.raises(json.JSONDecodeError):
        process_logs(input_file, fake_output_dir)


def test_process_logs_output_dir_creation(fs, test_logs_file):
    """Test that output directory is created if it doesn't exist when processing raw keylogs."""
    output_dir = Path("/fake/new/output/dir")

    # Process keylogs - should create output directory
    process_logs(test_logs_file, output_dir)

    # Verify output directory was created
    assert output_dir.exists()
    assert output_dir.is_dir()

    # Verify output files were created
    expected_files = [
        "level_1_actions_per_session.json",
        "level_2_actions_per_session.json",
        "level_3_actions_per_session.json",
        "action_type_with_priority_per_session.json",
    ]

    for filename in expected_files:
        assert (output_dir / filename).exists()


def test_process_logs_with_plugins(
    test_logs_file, fs, fake_output_dir, monkeypatch, mock_plugin, mock_plugin2
):
    """Test processing logs with active plugins."""
    # Mock the ACTIVE_PLUGINS list in both places where it's used
    monkeypatch.setattr(
        "coauthor_interface.thought_toolkit.parse_all_consolidated.ACTIVE_PLUGINS",
        [mock_plugin, mock_plugin2],
    )
    monkeypatch.setattr(
        "coauthor_interface.thought_toolkit.parser_all_levels.ACTIVE_PLUGINS",
        [mock_plugin, mock_plugin2],
    )

    # Process the keylogs
    process_logs(test_logs_file, fake_output_dir)

    # Check that the output file with priority actions exists
    output_file = fake_output_dir / "action_type_with_priority_per_session.json"
    assert output_file.exists()

    # Verify the priority actions contain plugin names
    with open(output_file, encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) > 0

        # Debug: Print all level_3_action_types found
        all_level_3_types = set()
        for session_actions in data.values():
            for action in session_actions:
                if "level_3_action_type" in action:
                    all_level_3_types.add(action["level_3_action_type"])
        print(f"Found level_3_action_types: {all_level_3_types}")

        # Check that plugin names are logged in the output file
        for session_actions in data.values():
            for action in session_actions:
                if "level_3_action_type" in action:
                    # Debug: Print action details if it doesn't match expected plugin names
                    if action["level_3_action_type"] not in [
                        mock_plugin.get_plugin_name(),
                        mock_plugin2.get_plugin_name(),
                    ]:
                        print(f"Unexpected action: {action}")
                    assert action["level_3_action_type"] in [
                        mock_plugin.get_plugin_name(),
                        mock_plugin2.get_plugin_name(),
                    ]


def test_process_logs_with_empty_plugins(test_logs_file, fs, fake_output_dir, monkeypatch):
    """Test processing logs with empty ACTIVE_PLUGINS list."""
    # Mock the ACTIVE_PLUGINS list to be empty in both places
    monkeypatch.setattr("coauthor_interface.thought_toolkit.parse_all_consolidated.ACTIVE_PLUGINS", [])
    monkeypatch.setattr("coauthor_interface.thought_toolkit.parser_all_levels.ACTIVE_PLUGINS", [])

    # Process the keylogs - should not raise any errors
    process_logs(test_logs_file, fake_output_dir)

    # Check that the output file with priority actions exists
    output_file = fake_output_dir / "action_type_with_priority_per_session.json"
    assert output_file.exists()

    # Verify the file contains valid JSON
    with open(output_file, encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) > 0


def test_plugin_detection_called(test_logs_file, fs, fake_output_dir, monkeypatch, mock_plugin):
    """Test that plugin detection_detected method is called during processing."""
    # Create a spy for the detection_detected method
    detection_called = False

    def mock_detection_detected(action):
        nonlocal detection_called
        detection_called = True
        return mock_plugin.detection_detected(action)

    # Create a modified mock plugin with the spy
    class SpyMockPlugin(Plugin):
        @staticmethod
        def get_plugin_name() -> str:
            return mock_plugin.get_plugin_name()

        @staticmethod
        def detection_detected(action):
            return mock_detection_detected(action)

        @staticmethod
        def intervention_action() -> Intervention:
            return mock_plugin.intervention_action()

    # Mock the ACTIVE_PLUGINS list with our spy plugin in both places
    monkeypatch.setattr(
        "coauthor_interface.thought_toolkit.parse_all_consolidated.ACTIVE_PLUGINS",
        [SpyMockPlugin()],
    )
    monkeypatch.setattr(
        "coauthor_interface.thought_toolkit.parser_all_levels.ACTIVE_PLUGINS",
        [SpyMockPlugin()],
    )

    # Process the keylogs
    process_logs(test_logs_file, fake_output_dir)

    # Verify that detection_detected was called
    assert detection_called, "Plugin detection_detected method was not called during processing"
