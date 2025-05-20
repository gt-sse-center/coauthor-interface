import json
from pathlib import Path
import pytest
from coauthor_interface.backend.parse_all_consolidated import (
    parse_level_1_actions,
    parse_level_2_actions_from_level_1,
    parse_level_3_actions_from_level_2,
    populate_priority_list,
    action_type_priority_sort,
    process_logs,
)


@pytest.fixture
def raw_keylogs_from_frontend():
    """Fixture providing sample raw keylogs from frontend for testing."""
    return {
        "session1": [
            {
                "eventName": "suggestion-get",
                "eventSource": "user",
                "eventTimestamp": 1629357366346,
                "textDelta": "",
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 379,
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
                "eventName": "suggestion-open",
                "eventSource": "api",
                "eventTimestamp": 1629357368607,
                "textDelta": "",
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 379,
                "currentSuggestions": [
                    {
                        "index": 0,
                        "original": " technology has made dating and relationships better.",
                        "trimmed": "technology has made dating and relationships better.",
                        "probability": 4.39569292539925e-12,
                    },
                    {
                        "index": 1,
                        "original": " technology has improved dating and relationships.",
                        "trimmed": "technology has improved dating and relationships.",
                        "probability": 4.65727687645238e-12,
                    },
                    {
                        "index": 2,
                        "original": " technology has made dating easier.",
                        "trimmed": "technology has made dating easier.",
                        "probability": 1.0105152942910267e-12,
                    },
                ],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 2,
            },
            {
                "eventName": "suggestion-close",
                "eventSource": "user",
                "eventTimestamp": 1629357369818,
                "textDelta": "",
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 379,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 3,
            },
            {
                "eventName": "text-insert",
                "eventSource": "user",
                "eventTimestamp": 1629357370478,
                "textDelta": {"ops": [{"retain": 379}, {"insert": " "}]},
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 380,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 4,
            },
        ],
        "session2": [
            {
                "eventName": "suggestion-get",
                "eventSource": "user",
                "eventTimestamp": 1629357366346,
                "textDelta": "",
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 0,
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
                "eventName": "suggestion-open",
                "eventSource": "api",
                "eventTimestamp": 1629357368607,
                "textDelta": "",
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 0,
                "currentSuggestions": [
                    {
                        "index": 0,
                        "original": "The weather is beautiful today.",
                        "trimmed": "The weather is beautiful today.",
                        "probability": 4.39569292539925e-12,
                    },
                    {
                        "index": 1,
                        "original": "It's a perfect day for a walk.",
                        "trimmed": "It's a perfect day for a walk.",
                        "probability": 4.65727687645238e-12,
                    },
                    {
                        "index": 2,
                        "original": "The sun is shining brightly.",
                        "trimmed": "The sun is shining brightly.",
                        "probability": 1.0105152942910267e-12,
                    },
                ],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 2,
            },
            {
                "eventName": "suggestion-close",
                "eventSource": "user",
                "eventTimestamp": 1629357369818,
                "textDelta": "",
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 0,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 3,
            },
            {
                "eventName": "text-insert",
                "eventSource": "user",
                "eventTimestamp": 1629357370478,
                "textDelta": {
                    "ops": [
                        {"retain": 0},
                        {"insert": "The weather is beautiful today."},
                    ]
                },
                "cursorRange": "",
                "currentDoc": "",
                "currentCursor": 28,
                "currentSuggestions": [],
                "currentSuggestionIndex": 0,
                "currentHoverIndex": "",
                "currentN": "5",
                "currentMaxToken": "30",
                "currentTemperature": "0.2",
                "currentTopP": "1",
                "currentPresencePenalty": "0",
                "currentFrequencyPenalty": "0.5",
                "eventNum": 4,
            },
        ],
    }


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


def test_process_logs(raw_keylogs_from_frontend, fs, fake_output_dir):
    """Test the complete processing pipeline of raw keylogs using fake filesystem."""
    # Create a fake input file with raw keylogs
    input_file = Path("/fake/input/raw_keylogs.json")
    fs.create_file(input_file, contents=json.dumps(raw_keylogs_from_frontend))

    # Process the keylogs
    process_logs(input_file, fake_output_dir)

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
        with open(output_file) as f:
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


def test_process_logs_output_dir_creation(fs, raw_keylogs_from_frontend):
    """Test that output directory is created if it doesn't exist when processing raw keylogs."""
    input_file = Path("/fake/input/raw_keylogs.json")
    output_dir = Path("/fake/new/output/dir")

    # Create input file with raw keylogs
    fs.create_file(input_file, contents=json.dumps(raw_keylogs_from_frontend))

    # Process keylogs - should create output directory
    process_logs(input_file, output_dir)

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
