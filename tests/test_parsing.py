"""
Tests for the parsing module.
"""

import numpy as np
from types import SimpleNamespace

from coauthor_interface.backend.parsing import (
    parse_prompt,
    parse_modified_prompt,
    parse_probability,
    parse_suggestion,
    filter_suggestions,
)


class TestParsePrompt:
    """Test cases for parse_prompt function."""

    def test_parse_prompt_basic(self):
        """Test basic prompt parsing with simple text."""
        text = "Hello world\nThis is a test"
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert result["effective_prompt"] == "Hello world\nThis is a test"
        assert result["after_prompt"] == ""

    def test_parse_prompt_with_trailing_whitespace(self):
        """Test prompt parsing with trailing whitespace."""
        text = "Hello world\nThis is a test   \n"
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert result["effective_prompt"] == "Hello world\nThis is a test   \n"
        assert result["after_prompt"] == ""

    def test_parse_prompt_with_trailing_spaces_only(self):
        """Test prompt parsing with only trailing spaces."""
        text = "Hello world   "
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert result["effective_prompt"] == "Hello world"
        assert result["after_prompt"] == "   "

    def test_parse_prompt_long_text_truncation(self):
        """Test prompt parsing with text that exceeds max length."""
        # Create text longer than max_prompt_len
        long_text = "A" * 5000
        max_tokens = 100
        context_window_size = 1000
        max_prompt_len = (context_window_size - max_tokens) * 4  # 3600

        result = parse_prompt(long_text, max_tokens, context_window_size)

        assert result["text_len"] == len(long_text)
        assert len(result["before_prompt"]) > 0
        assert len(result["effective_prompt"]) <= max_prompt_len
        assert result["after_prompt"] == ""

    def test_parse_prompt_empty_text(self):
        """Test prompt parsing with empty text."""
        text = ""
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == 0
        assert result["before_prompt"] == ""
        assert result["effective_prompt"] == ""
        assert result["after_prompt"] == ""

    def test_parse_prompt_single_line(self):
        """Test prompt parsing with single line text."""
        text = "Single line text"
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert result["effective_prompt"] == "Single line text"
        assert result["after_prompt"] == ""

    def test_parse_prompt_multiple_lines_with_whitespace(self):
        """Test prompt parsing with multiple lines where only last line has whitespace."""
        text = "Line 1\nLine 2\nLine 3   "
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert result["effective_prompt"] == "Line 1\nLine 2\nLine 3"
        assert result["after_prompt"] == "   "

    def test_parse_prompt_with_trailing_newline_and_spaces(self):
        """Test prompt parsing with trailing newline and spaces on the last non-empty line."""
        text = "Hello world\nThis is a test   \n"
        max_tokens = 100
        context_window_size = 1000

        result = parse_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        # The function only strips whitespace from the last line, but if the last line
        # is empty (just a newline), then after_prompt will be empty
        assert result["effective_prompt"] == "Hello world\nThis is a test   \n"
        assert result["after_prompt"] == ""


class TestParseModifiedPrompt:
    """Test cases for parse_modified_prompt function."""

    def test_parse_modified_prompt_basic(self):
        """Test basic modified prompt parsing."""
        text = "Hello world\nThis is a test"
        max_tokens = 100
        context_window_size = 1000

        result = parse_modified_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert "Hello world\nThis is a test" in result["effective_prompt"]
        assert "Based on the text above, ask four questions" in result["effective_prompt"]
        assert result["after_prompt"] == ""

    def test_parse_modified_prompt_with_trailing_whitespace(self):
        """Test modified prompt parsing with trailing whitespace."""
        text = "Hello world\nThis is a test   \n"
        max_tokens = 100
        context_window_size = 1000

        result = parse_modified_prompt(text, max_tokens, context_window_size)

        assert result["text_len"] == len(text)
        assert result["before_prompt"] == ""
        assert "Hello world\nThis is a test   \n" in result["effective_prompt"]
        assert "Based on the text above, ask four questions" in result["effective_prompt"]
        assert result["after_prompt"] == ""

    def test_parse_modified_prompt_long_text_truncation(self):
        """Test modified prompt parsing with text that exceeds max length."""
        long_text = "A" * 5000
        max_tokens = 100
        context_window_size = 1000

        result = parse_modified_prompt(long_text, max_tokens, context_window_size)

        assert result["text_len"] == len(long_text)
        assert len(result["before_prompt"]) > 0
        assert "Based on the text above, ask four questions" in result["effective_prompt"]
        assert result["after_prompt"] == ""

    def test_parse_modified_prompt_socratic_format(self):
        """Test that the socratic modification is properly formatted."""
        text = "Sample text"
        max_tokens = 100
        context_window_size = 1000

        result = parse_modified_prompt(text, max_tokens, context_window_size)

        expected_format = "\n\nBased on the text above, ask four questions on what has not yet been addressed in the writing. \
                Please ask questions in the following format:\n1. [QUESTION 1]\n2. [QUESTION 2]\n3. [QUESTION 3]\n4. [QUESTION 4"

        assert expected_format in result["effective_prompt"]


class TestParseProbability:
    """Test cases for parse_probability function."""

    def test_parse_probability_basic(self):
        """Test basic probability parsing."""
        logprobs = SimpleNamespace()
        logprobs.token_logprobs = [-0.5, -0.3, -0.2]

        result = parse_probability(logprobs)
        expected_prob = np.e ** (-0.5 - 0.3 - 0.2) * 100

        assert abs(result - expected_prob) < 1e-10

    def test_parse_probability_single_token(self):
        """Test probability parsing with single token."""
        logprobs = SimpleNamespace()
        logprobs.token_logprobs = [-0.5]

        result = parse_probability(logprobs)
        expected_prob = np.e ** (-0.5) * 100

        assert abs(result - expected_prob) < 1e-10

    def test_parse_probability_zero_logprob(self):
        """Test probability parsing with zero log probability."""
        logprobs = SimpleNamespace()
        logprobs.token_logprobs = [0.0, 0.0]

        result = parse_probability(logprobs)
        expected_prob = np.e ** (0.0) * 100

        assert abs(result - expected_prob) < 1e-10

    def test_parse_probability_negative_logprobs(self):
        """Test probability parsing with negative log probabilities."""
        logprobs = SimpleNamespace()
        logprobs.token_logprobs = [-1.0, -2.0, -3.0]

        result = parse_probability(logprobs)
        expected_prob = np.e ** (-1.0 - 2.0 - 3.0) * 100

        assert abs(result - expected_prob) < 1e-10

    def test_parse_probability_empty_logprobs(self):
        """Test probability parsing with empty token logprobs."""
        logprobs = SimpleNamespace()
        logprobs.token_logprobs = []

        result = parse_probability(logprobs)
        expected_prob = np.e ** (0.0) * 100

        assert abs(result - expected_prob) < 1e-10


class TestParseSuggestion:
    """Test cases for parse_suggestion function."""

    def test_parse_suggestion_basic(self):
        """Test basic suggestion parsing."""
        suggestion = "This is a suggestion."
        after_prompt = ""
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "This is a suggestion."

    def test_parse_suggestion_with_after_prompt(self):
        """Test suggestion parsing with after_prompt prefix."""
        suggestion = "   This is a suggestion."
        after_prompt = "   "
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "This is a suggestion."

    def test_parse_suggestion_multiple_sentences(self):
        """Test suggestion parsing with multiple sentences."""
        suggestion = "First sentence. Second sentence. Third sentence."
        after_prompt = ""
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "First sentence."

    def test_parse_suggestion_with_newlines(self):
        """Test suggestion parsing with newlines in the first sentence."""
        suggestion = "First sentence\nwith newline. Second sentence."
        after_prompt = ""
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "First sentence"

    def test_parse_suggestion_no_period(self):
        """Test suggestion parsing when no period is found."""
        suggestion = "This is a suggestion without period"
        after_prompt = ""
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "This is a suggestion without period"

    def test_parse_suggestion_empty_suggestion(self):
        """Test suggestion parsing with empty suggestion."""
        suggestion = ""
        after_prompt = ""
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == ""

    def test_parse_suggestion_no_stop_rules(self):
        """Test suggestion parsing when stop_rules doesn't contain period."""
        suggestion = "This is a suggestion."
        after_prompt = ""
        stop_rules = "!"

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "This is a suggestion."

    def test_parse_suggestion_whitespace_preservation(self):
        """Test that whitespace before the first sentence is preserved."""
        suggestion = "   This is a suggestion. Second sentence."
        after_prompt = ""
        stop_rules = "."

        result = parse_suggestion(suggestion, after_prompt, stop_rules)

        assert result == "   This is a suggestion."


class TestFilterSuggestions:
    """Test cases for filter_suggestions function."""

    def test_filter_suggestions_basic(self):
        """Test basic suggestion filtering."""
        suggestions = [
            ("suggestion1", 0.8, "source1"),
            ("suggestion2", 0.6, "source2"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 2
        assert result[0] == ("suggestion1", 0.8, "source1")
        assert result[1] == ("suggestion2", 0.6, "source2")
        assert counts["empty_cnt"] == 0
        assert counts["duplicate_cnt"] == 0
        assert counts["bad_cnt"] == 0

    def test_filter_suggestions_empty_strings(self):
        """Test filtering out empty strings."""
        suggestions = [
            ("", 0.8, "source1"),
            ("suggestion2", 0.6, "source2"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("suggestion2", 0.6, "source2")
        assert counts["empty_cnt"] == 1
        assert counts["duplicate_cnt"] == 0
        assert counts["bad_cnt"] == 0

    def test_filter_suggestions_duplicates(self):
        """Test filtering out duplicates."""
        suggestions = [
            ("suggestion1", 0.8, "source1"),
            ("suggestion1", 0.6, "source2"),  # Duplicate
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("suggestion1", 0.8, "source1")
        assert counts["empty_cnt"] == 0
        assert counts["duplicate_cnt"] == 1
        assert counts["bad_cnt"] == 0

    def test_filter_suggestions_prev_duplicates(self):
        """Test filtering out suggestions that exist in prev_suggestions."""
        suggestions = [
            ("suggestion1", 0.8, "source1"),
            ("suggestion2", 0.6, "source2"),
        ]
        prev_suggestions = [{"original": "suggestion1"}]
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("suggestion2", 0.6, "source2")
        assert counts["empty_cnt"] == 0
        assert counts["duplicate_cnt"] == 1
        assert counts["bad_cnt"] == 0

    def test_filter_suggestions_blocklist(self):
        """Test filtering out suggestions with blocklisted words."""
        suggestions = [
            ("This is a bad suggestion", 0.8, "source1"),
            ("This is a good suggestion", 0.6, "source2"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("This is a good suggestion", 0.6, "source2")
        assert counts["empty_cnt"] == 0
        assert counts["duplicate_cnt"] == 0
        assert counts["bad_cnt"] == 1

    def test_filter_suggestions_case_insensitive_blocklist(self):
        """Test that blocklist checking is case insensitive."""
        suggestions = [
            ("This is a BAD suggestion", 0.8, "source1"),
            ("This is a good suggestion", 0.6, "source2"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("This is a good suggestion", 0.6, "source2")
        assert counts["bad_cnt"] == 1

    def test_filter_suggestions_disable_empty_filter(self):
        """Test filtering with empty string filtering disabled."""
        suggestions = [
            ("", 0.8, "source1"),
            ("suggestion2", 0.6, "source2"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(
            suggestions, prev_suggestions, blocklist, remove_empty_strings=False
        )

        assert len(result) == 2
        assert counts["empty_cnt"] == 0

    def test_filter_suggestions_disable_duplicate_filter(self):
        """Test filtering with duplicate filtering disabled."""
        suggestions = [
            ("suggestion1", 0.8, "source1"),
            ("suggestion1", 0.6, "source2"),  # Duplicate
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist, remove_duplicates=False)

        assert len(result) == 2
        assert counts["duplicate_cnt"] == 0

    def test_filter_suggestions_disable_blocklist(self):
        """Test filtering with blocklist filtering disabled."""
        suggestions = [
            ("This is a bad suggestion", 0.8, "source1"),
            ("This is a good suggestion", 0.6, "source2"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist, use_blocklist=False)

        assert len(result) == 2
        assert counts["bad_cnt"] == 0

    def test_filter_suggestions_multiple_filters(self):
        """Test multiple filters working together."""
        suggestions = [
            ("", 0.9, "source1"),  # Empty
            ("bad suggestion", 0.8, "source2"),  # Blocklisted
            ("good suggestion", 0.7, "source3"),  # Good
            ("good suggestion", 0.6, "source4"),  # Duplicate
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("good suggestion", 0.7, "source3")
        assert counts["empty_cnt"] == 1
        assert counts["duplicate_cnt"] == 1
        assert counts["bad_cnt"] == 1

    def test_filter_suggestions_empty_input(self):
        """Test filtering with empty input."""
        suggestions = []
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 0
        assert counts["empty_cnt"] == 0
        assert counts["duplicate_cnt"] == 0
        assert counts["bad_cnt"] == 0

    def test_filter_suggestions_complex_blocklist_matching(self):
        """Test complex blocklist word matching."""
        suggestions = [
            ("The offensive word is here", 0.8, "source1"),
            ("This contains bad language", 0.7, "source2"),
            ("Clean suggestion", 0.6, "source3"),
        ]
        prev_suggestions = []
        blocklist = {"bad", "offensive"}

        result, counts = filter_suggestions(suggestions, prev_suggestions, blocklist)

        assert len(result) == 1
        assert result[0] == ("Clean suggestion", 0.6, "source3")
        assert counts["bad_cnt"] == 2
