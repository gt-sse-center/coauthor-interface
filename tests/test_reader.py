import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coauthor_interface.backend.reader import (
    read_access_codes,
    read_api_keys,
    read_blocklist,
    read_examples,
    read_log,
    read_prompts,
    update_metadata,
)


class TestReader:
    """Test cases for reader.py functions."""

    @pytest.fixture
    def config_dir(self, fs):
        """Create a temporary config directory in fake filesystem."""
        config_path = Path("/tmp/config")
        fs.create_dir(config_path)
        return config_path

    def test_read_api_keys_success(self, fs, config_dir):
        """Test successful reading of API keys."""
        # Create API keys CSV file
        api_keys_content = "host,domain,key\nopenai,default,sk-test123\nanthropic,story,sk-ant-test456"
        api_keys_file = config_dir / "api_keys.csv"
        fs.create_file(str(api_keys_file), contents=api_keys_content)

        result = read_api_keys(config_dir)

        expected = {
            ("openai", "default"): "sk-test123",
            ("anthropic", "story"): "sk-ant-test456",
        }
        assert result == expected

    def test_read_api_keys_file_not_found(self, config_dir):
        """Test reading API keys when file doesn't exist."""
        with pytest.raises(RuntimeError, match="Cannot find API keys in the file"):
            read_api_keys(config_dir)

    def test_read_log_json(self, fs):
        """Test reading JSON log file."""
        log_data = [{"session_id": "123", "message": "test"}]
        log_file = Path("/tmp/test.json")
        fs.create_file(str(log_file), contents=json.dumps(log_data))

        result = read_log(log_file)

        assert result == log_data

    def test_read_log_jsonl(self, fs):
        """Test reading JSONL log file."""
        log_data = [
            {"session_id": "123", "message": "test1"},
            {"session_id": "456", "message": "test2"},
        ]
        log_content = "\n".join(json.dumps(item) for item in log_data)
        log_file = Path("/tmp/test.jsonl")
        fs.create_file(str(log_file), contents=log_content)

        result = read_log(log_file)

        assert result == log_data

    def test_read_log_file_not_found(self):
        """Test reading log file when it doesn't exist."""
        log_file = Path("/tmp/nonexistent.json")
        with pytest.raises(FileNotFoundError, match="Log file not found"):
            read_log(log_file)

    def test_read_log_unknown_extension(self, fs):
        """Test reading log file with unknown extension."""
        log_file = Path("/tmp/test.txt")
        fs.create_file(str(log_file), contents="test content")

        result = read_log(log_file)

        assert result == []

    def test_read_examples_success(self, fs, config_dir):
        """Test successful reading of examples."""
        examples_dir = config_dir / "examples"
        fs.create_dir(str(examples_dir))

        # Create example files
        example1_content = "This is example 1\\nwith newlines"
        example2_content = "This is example 2"
        fs.create_file(str(examples_dir / "example1.txt"), contents=example1_content)
        fs.create_file(str(examples_dir / "example2.txt"), contents=example2_content)

        result = read_examples(config_dir)

        expected = {
            "na": "",
            "example1": "This is example 1\nwith newlines ",
            "example2": "This is example 2 ",
        }
        assert result == expected

    def test_read_examples_directory_not_found(self, config_dir):
        """Test reading examples when directory doesn't exist."""
        result = read_examples(config_dir)

        assert result == {"na": ""}

    def test_read_prompts_success(self, fs, config_dir):
        """Test successful reading of prompts."""
        prompts_content = "1\ttest_prompt\tThis is a test prompt\\nwith newlines"
        prompts_file = config_dir / "prompts.tsv"
        fs.create_file(str(prompts_file), contents=prompts_content)

        result = read_prompts(config_dir)

        expected = {"na": "", "test_prompt": "This is a test prompt\nwith newlines"}
        assert result == expected

    def test_read_prompts_file_not_found(self, config_dir):
        """Test reading prompts when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Prompts file not found"):
            read_prompts(config_dir)

    def test_read_prompts_invalid_row(self, fs, config_dir):
        """Test reading prompts with invalid row format."""
        prompts_content = "code\tprompt_code\n1\ttest_prompt\tThis is a test prompt\n2\tinvalid_row"
        prompts_file = config_dir / "prompts.tsv"
        fs.create_file(str(prompts_file), contents=prompts_content)

        result = read_prompts(config_dir)

        expected = {"na": "", "test_prompt": "This is a test prompt"}
        assert result == expected

    def test_read_access_codes_success(self, fs, config_dir):
        """Test successful reading of access codes."""
        access_code_content = (
            "access_code,model,host,domain\ncode123,gpt-4,openai,default\ncode456,claude,anthropic,story"
        )
        access_code_file = config_dir / "access_code_test.csv"
        fs.create_file(str(access_code_file), contents=access_code_content)

        # Mock AccessCodeConfig
        with patch("coauthor_interface.backend.reader.AccessCodeConfig") as mock_config_class:
            mock_config1 = Mock()
            mock_config2 = Mock()
            mock_config_class.side_effect = [mock_config1, mock_config2]

            result = read_access_codes(config_dir)

            assert len(result) == 2
            assert "code123" in result
            assert "code456" in result
            assert result["code123"] == mock_config1
            assert result["code456"] == mock_config2

    def test_read_access_codes_directory_not_found(self):
        """Test reading access codes when directory doesn't exist."""
        with pytest.raises(RuntimeError, match="Cannot find access code at"):
            read_access_codes("/nonexistent/dir")

    def test_read_access_codes_missing_access_code_column(self, fs, config_dir):
        """Test reading access codes with missing access_code column."""
        access_code_content = "model,host,domain\ncode123,gpt-4,openai,default"
        access_code_file = config_dir / "access_code_test.csv"
        fs.create_file(str(access_code_file), contents=access_code_content)

        result = read_access_codes(config_dir)

        assert result == {}

    def test_update_metadata_success(self, fs):
        """Test successful updating of metadata."""
        metadata = {}
        metadata_content = '{"session_id": "123", "data": "test1"}\n{"session_id": "456", "data": "test2"}'
        metadata_file = Path("/tmp/metadata.jsonl")
        fs.create_file(str(metadata_file), contents=metadata_content)

        result = update_metadata(metadata, metadata_file)

        expected = {
            "123": {"session_id": "123", "data": "test1"},
            "456": {"session_id": "456", "data": "test2"},
        }
        assert result == expected

    def test_update_metadata_file_not_found(self):
        """Test updating metadata when file doesn't exist."""
        metadata = {}
        metadata_file = Path("/tmp/nonexistent.jsonl")

        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            update_metadata(metadata, metadata_file)

    def test_update_metadata_empty_lines(self, fs):
        """Test updating metadata with empty lines."""
        metadata = {}
        metadata_content = '{"session_id": "123", "data": "test1"}\n\n{"session_id": "456", "data": "test2"}'
        metadata_file = Path("/tmp/metadata.jsonl")
        fs.create_file(str(metadata_file), contents=metadata_content)

        result = update_metadata(metadata, metadata_file)

        expected = {
            "123": {"session_id": "123", "data": "test1"},
            "456": {"session_id": "456", "data": "test2"},
        }
        assert result == expected

    def test_read_blocklist_success(self, fs, config_dir):
        """Test successful reading of blocklist."""
        blocklist_content = "blocked_user1\nblocked_user2\n\nblocked_user3"
        blocklist_file = config_dir / "blocklist.txt"
        fs.create_file(str(blocklist_file), contents=blocklist_content)

        result = read_blocklist(config_dir)

        expected = {"blocked_user1", "blocked_user2", "blocked_user3"}
        assert result == expected

    def test_read_blocklist_file_not_found(self, config_dir):
        """Test reading blocklist when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Blocklist file not found"):
            read_blocklist(config_dir)

    def test_read_blocklist_empty_file(self, fs, config_dir):
        """Test reading empty blocklist file."""
        blocklist_file = config_dir / "blocklist.txt"
        fs.create_file(str(blocklist_file), contents="")

        result = read_blocklist(config_dir)

        assert result == set()

    def test_read_blocklist_with_whitespace(self, fs, config_dir):
        """Test reading blocklist with whitespace around entries."""
        blocklist_content = "  blocked_user1  \nblocked_user2\n  blocked_user3  "
        blocklist_file = config_dir / "blocklist.txt"
        fs.create_file(str(blocklist_file), contents=blocklist_content)

        result = read_blocklist(config_dir)

        expected = {"blocked_user1", "blocked_user2", "blocked_user3"}
        assert result == expected
