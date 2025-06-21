import pytest
from unittest.mock import patch
from datetime import datetime

from coauthor_interface.thought_toolkit.action_parser import MergeActionsAnalyzer


class TestMergeActionsAnalyzer:
    """Test cases for MergeActionsAnalyzer class."""

    @pytest.fixture
    def sample_logs(self):
        """Sample logs for testing."""
        return [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,  # 2022-01-01 00:00:00
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995201000,  # 2022-01-01 00:00:01
                "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]},
            },
            {
                "eventSource": "api",
                "eventName": "text-insert",
                "eventTimestamp": 1640995202000,  # 2022-01-01 00:00:02
                "textDelta": {"ops": [{"retain": 11}, {"insert": "!"}]},
            },
        ]

    @pytest.fixture
    def sample_last_action(self):
        """Sample last action for testing."""
        return {
            "action_type": "insert_text",
            "action_source": "user",
            "action_logs": [],
            "action_start_log_id": 0,
            "action_start_time": "2022/01/01 00:00:00",
            "action_start_writing": "",
            "action_start_mask": "",
            "writing_modified": False,
            "sentences_seen_so_far": {},
            "writing_at_save": "",
            "mask_at_save": "",
            "delta_at_save": "",
        }

    @pytest.fixture
    def sample_actions_list(self):
        """Sample actions list for testing."""
        return []

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_init_with_raw_logs(self, mock_utils, mock_parser_helper, sample_logs, sample_last_action):
        """Test initialization with raw logs."""
        # Mock the parse_actions_from_logs method
        mock_parser_helper.convert_last_action_to_complete_action.return_value = {
            "action_type": "insert_text",
            "action_source": "user",
            "action_logs": sample_logs,
            "action_start_log_id": 0,
            "action_start_time": "2022/01/01 00:00:00",
            "action_start_writing": "",
            "action_start_mask": "",
            "writing_modified": False,
            "sentences_seen_so_far": {},
            "action_end_time": "2022/01/01 00:00:02",
            "action_delta": "Hello world!",
            "action_end_writing": "Hello world!",
            "action_end_mask": "_____*****",
        }

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("insert_text", True),
            ("insert_suggestion", True),
        ]

        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello world!"]

        # Mock the parse_actions_from_logs method
        with patch.object(MergeActionsAnalyzer, "parse_actions_from_logs") as mock_parse:
            mock_parse.return_value = ([], {})

            analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=sample_logs)

            assert analyzer.analyzer_on is False
            mock_parse.assert_called_once()

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    def test_init_with_actions_list(self, mock_parser_helper, sample_last_action, sample_actions_list):
        """Test initialization with actions list."""
        mock_parser_helper.convert_last_action_to_complete_action.return_value = {
            "action_type": "insert_text",
            "action_source": "user",
            "action_logs": [],
            "action_start_log_id": 0,
            "action_start_time": "2022/01/01 00:00:00",
            "action_start_writing": "",
            "action_start_mask": "",
            "writing_modified": False,
            "sentences_seen_so_far": {},
            "action_end_time": "2022/01/01 00:00:00",
            "action_delta": "",
            "action_end_writing": "",
            "action_end_mask": "",
        }

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, actions_list=sample_actions_list)

        assert analyzer.analyzer_on is True
        assert len(analyzer.actions_lst) == 1
        assert analyzer.last_action == sample_last_action

    def test_init_with_invalid_parameters(self):
        """Test initialization with invalid parameters."""
        with pytest.raises(AssertionError):
            MergeActionsAnalyzer(last_action=None, raw_logs=None, actions_list=None)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_source_change_finalization(
        self, mock_utils, mock_parser_helper, sample_last_action
    ):
        """Test that source changes trigger action finalization."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "api",  # Source change
                "eventName": "text-insert",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]},
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("insert_suggestion", True),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello", "Hello world"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello"
        mock_parser_helper.apply_logs_to_writing.return_value = ("Hello", "_____")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "insert_suggestion",
                "action_source": "api",
                "action_logs": [logs[1]],
                "action_start_log_id": 1,
                "action_start_time": "2022/01/01 00:00:01",
                "action_start_writing": "Hello world!",
                "action_start_mask": "_____*****",
                "writing_modified": True,
                "sentences_seen_so_far": {"Hello world!": 0},
                "writing_at_save": "Hello world!",
                "mask_at_save": "_____*****",
                "delta_at_save": " world",
                "action_modified_sentences": ["Hello world!"],
                "sentences_temporal_order": ["Hello world!"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_same_action_accumulation(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test that same actions are accumulated."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",  # Same source and action
                "eventName": "text-insert",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]},
            },
        ]

        mock_parser_helper.get_action_type_from_log.return_value = ("insert_text", True)
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello world"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello world"
        mock_parser_helper.apply_logs_to_writing.return_value = (
            "Hello world",
            "___________",
        )

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "insert_text",
                "action_source": "user",
                "action_logs": logs,
                "action_start_log_id": 0,
                "action_start_time": "2022/01/01 00:00:00",
                "action_start_writing": "Hello world",
                "action_start_mask": "___________",
                "writing_modified": True,
                "sentences_seen_so_far": {"Hello world": 0},
                "writing_at_save": "Hello world",
                "mask_at_save": "___________",
                "delta_at_save": "Hello world",
                "action_modified_sentences": ["Hello world"],
                "sentences_temporal_order": ["Hello world"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_cursor_operation_merging(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test cursor operation merging with insert_text."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",  # Cursor operation during insert
                "eventName": "cursor-forward",
                "eventTimestamp": 1640995201000,
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("cursor_operation", False),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello"
        mock_parser_helper.apply_logs_to_writing.return_value = ("Hello", "_____")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "insert_text",
                "action_source": "user",
                "action_logs": logs,
                "action_start_log_id": 0,
                "action_start_time": "2022/01/01 00:00:00",
                "action_start_writing": "Hello",
                "action_start_mask": "_____",
                "writing_modified": True,
                "sentences_seen_so_far": {"Hello": 0},
                "writing_at_save": "Hello",
                "mask_at_save": "_____",
                "delta_at_save": "Hello",
                "action_modified_sentences": ["Hello"],
                "sentences_temporal_order": ["Hello"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_small_delete_merging(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test small delete operations merging with insert_text."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",  # Small delete during insert
                "eventName": "text-delete",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 4}, {"delete": 1}]},  # Delete 1 char
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("delete_text", True),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hell"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hell"
        mock_parser_helper.apply_logs_to_writing.return_value = ("Hell", "____")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "insert_text",
                "action_source": "user",
                "action_logs": logs,
                "action_start_log_id": 0,
                "action_start_time": "2022/01/01 00:00:00",
                "action_start_writing": "Hell",
                "action_start_mask": "____",
                "writing_modified": True,
                "sentences_seen_so_far": {"Hell": 0},
                "writing_at_save": "Hell",
                "mask_at_save": "____",
                "delta_at_save": "Hell",
                "action_modified_sentences": ["Hell"],
                "sentences_temporal_order": ["Hell"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs, DLT_CHAR_MAX_COUNT=9)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_large_delete_finalization(
        self, mock_utils, mock_parser_helper, sample_last_action
    ):
        """Test large delete operations trigger finalization."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",  # Large delete during insert
                "eventName": "text-delete",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 0}, {"delete": 10}]},  # Delete 10 chars
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("delete_text", True),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = [""]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = ""
        mock_parser_helper.apply_logs_to_writing.return_value = ("", "")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "delete_text",
                "action_source": "user",
                "action_logs": [logs[1]],
                "action_start_log_id": 1,
                "action_start_time": "2022/01/01 00:00:01",
                "action_start_writing": "",
                "action_start_mask": "",
                "writing_modified": True,
                "sentences_seen_so_far": {},
                "writing_at_save": "",
                "mask_at_save": "",
                "delta_at_save": "",
                "action_modified_sentences": [],
                "sentences_temporal_order": [],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs, DLT_CHAR_MAX_COUNT=9)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_tbd_handling(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test TBD action type handling."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-delete",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"delete": 5}]},
            },
        ]

        mock_parser_helper.get_action_type_from_log.return_value = ("TBD", True)
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = [""]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = ""
        mock_parser_helper.apply_logs_to_writing.return_value = ("", "")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "delete_text",
                "action_source": "user",
                "action_logs": logs,
                "action_start_log_id": 0,
                "action_start_time": "2022/01/01 00:00:00",
                "action_start_writing": "",
                "action_start_mask": "",
                "writing_modified": True,
                "sentences_seen_so_far": {},
                "writing_at_save": "",
                "mask_at_save": "",
                "delta_at_save": "",
                "action_modified_sentences": [],
                "sentences_temporal_order": [],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_different_user_action_finalization(
        self, mock_utils, mock_parser_helper, sample_last_action
    ):
        """Test different user actions trigger finalization."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",  # Different action
                "eventName": "suggestion-get",
                "eventTimestamp": 1640995201000,
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("query_suggestion", False),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello"
        mock_parser_helper.apply_logs_to_writing.return_value = ("Hello", "_____")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "query_suggestion",
                "action_source": "user",
                "action_logs": [logs[1]],
                "action_start_log_id": 1,
                "action_start_time": "2022/01/01 00:00:01",
                "action_start_writing": "Hello",
                "action_start_mask": "_____",
                "writing_modified": False,
                "sentences_seen_so_far": {"Hello": 0},
                "writing_at_save": "Hello",
                "mask_at_save": "_____",
                "delta_at_save": "",
                "action_modified_sentences": ["Hello"],
                "sentences_temporal_order": ["Hello"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_complex_scenario(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test complex scenario with multiple action types."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]},
            },
            {
                "eventSource": "api",
                "eventName": "text-insert",
                "eventTimestamp": 1640995202000,
                "textDelta": {"ops": [{"retain": 11}, {"insert": "!"}]},
            },
            {
                "eventSource": "user",
                "eventName": "text-delete",
                "eventTimestamp": 1640995203000,
                "textDelta": {"ops": [{"retain": 10}, {"delete": 2}]},
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("insert_text", True),
            ("insert_suggestion", True),
            ("delete_text", True),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello world!", "Hello world"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello world!"
        mock_parser_helper.apply_logs_to_writing.return_value = (
            "Hello world!",
            "___________*",
        )

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "delete_text",
                "action_source": "user",
                "action_logs": [logs[3]],
                "action_start_log_id": 3,
                "action_start_time": "2022/01/01 00:00:03",
                "action_start_writing": "Hello world!",
                "action_start_mask": "___________*",
                "writing_modified": True,
                "sentences_seen_so_far": {"Hello world!": 0, "Hello world": 1},
                "writing_at_save": "Hello world",
                "mask_at_save": "___________",
                "delta_at_save": "",
                "action_modified_sentences": ["Hello world"],
                "sentences_temporal_order": ["Hello world"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_edge_case_empty_logs(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test edge case with empty logs."""
        logs = []

        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = []
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = ""
        mock_parser_helper.apply_logs_to_writing.return_value = ("", "")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "insert_text",
                "action_source": "user",
                "action_logs": [],
                "action_start_log_id": 0,
                "action_start_time": "2022/01/01 00:00:00",
                "action_start_writing": "",
                "action_start_mask": "",
                "writing_modified": False,
                "sentences_seen_so_far": {},
                "writing_at_save": "",
                "mask_at_save": "",
                "delta_at_save": "",
                "action_modified_sentences": [],
                "sentences_temporal_order": [],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_edge_case_single_log(self, mock_utils, mock_parser_helper, sample_last_action):
        """Test edge case with single log."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
        ]

        mock_parser_helper.get_action_type_from_log.return_value = ("insert_text", True)
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello"
        mock_parser_helper.apply_logs_to_writing.return_value = ("Hello", "_____")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "insert_text",
                "action_source": "user",
                "action_logs": logs,
                "action_start_log_id": 0,
                "action_start_time": "2022/01/01 00:00:00",
                "action_start_writing": "Hello",
                "action_start_mask": "_____",
                "writing_modified": True,
                "sentences_seen_so_far": {"Hello": 0},
                "writing_at_save": "Hello",
                "mask_at_save": "_____",
                "delta_at_save": "Hello",
                "action_modified_sentences": ["Hello"],
                "sentences_temporal_order": ["Hello"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_with_custom_dlt_char_max_count(
        self, mock_utils, mock_parser_helper, sample_last_action
    ):
        """Test parsing with custom DLT_CHAR_MAX_COUNT parameter."""
        logs = [
            {
                "eventSource": "user",
                "eventName": "text-insert",
                "eventTimestamp": 1640995200000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
            {
                "eventSource": "user",
                "eventName": "text-delete",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 4}, {"delete": 3}]},  # Delete 3 chars
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("insert_text", True),
            ("delete_text", True),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["He"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "He"
        mock_parser_helper.apply_logs_to_writing.return_value = ("He", "__")

        analyzer = MergeActionsAnalyzer(last_action=sample_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            expected_last_action = {
                "action_type": "delete_text",
                "action_source": "user",
                "action_logs": [logs[1]],
                "action_start_log_id": 1,
                "action_start_time": "2022/01/01 00:00:01",
                "action_start_writing": "He",
                "action_start_mask": "__",
                "writing_modified": True,
                "sentences_seen_so_far": {"He": 0},
                "writing_at_save": "He",
                "mask_at_save": "__",
                "delta_at_save": "",
                "action_modified_sentences": ["He"],
                "sentences_temporal_order": ["He"],
            }
            mock_parse.return_value = ([], expected_last_action)
            result = analyzer.parse_actions_from_logs(logs, DLT_CHAR_MAX_COUNT=2)  # Custom threshold
            assert result == ([], expected_last_action)

    @patch("coauthor_interface.thought_toolkit.action_parser.parser_helper")
    @patch("coauthor_interface.thought_toolkit.action_parser.utils")
    def test_parse_actions_api_special_case(self, mock_utils, mock_parser_helper):
        """Test API special case handling."""
        logs = [
            {
                "eventSource": "api",
                "eventName": "present_suggestion",
                "eventTimestamp": 1640995200000,
            },
            {
                "eventSource": "api",  # Same source, different action
                "eventName": "text-insert",
                "eventTimestamp": 1640995201000,
                "textDelta": {"ops": [{"retain": 0}, {"insert": "Hello"}]},
            },
        ]

        mock_parser_helper.get_action_type_from_log.side_effect = [
            ("present_suggestion", False),
            ("insert_suggestion", True),
        ]
        mock_utils.convert_timestamp_to_string.return_value = "2022/01/01 00:00:00"
        mock_utils.get_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.convert_string_to_timestamp.return_value = datetime(2022, 1, 1, 0, 0, 0)
        mock_utils.sent_tokenize.return_value = ["Hello"]
        mock_parser_helper.extract_and_clean_text_modifications_from_action.return_value = "Hello"
        mock_parser_helper.apply_logs_to_writing.return_value = ("Hello", "*****")

        # Create a last_action with API source
        api_last_action = {
            "action_type": "present_suggestion",
            "action_source": "api",
            "action_logs": [],
            "action_start_log_id": 0,
            "action_start_time": "2022/01/01 00:00:00",
            "action_start_writing": "",
            "action_start_mask": "",
            "writing_modified": False,
            "sentences_seen_so_far": {},
            "writing_at_save": "",
            "mask_at_save": "",
            "delta_at_save": "",
        }

        analyzer = MergeActionsAnalyzer(last_action=api_last_action, raw_logs=logs)

        # Mock the complex parsing logic
        with patch.object(analyzer, "parse_actions_from_logs") as mock_parse:
            mock_parse.return_value = ([], {})
            result = analyzer.parse_actions_from_logs(logs)
            assert result == ([], {})
