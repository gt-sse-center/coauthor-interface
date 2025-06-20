"""Unit tests for the small group of modules in ``thought_toolkit``.

These tests exercise ``utils.py``, ``parser_helper.py`` and ``helper.py``. The
real spaCy dependency is optional so the tests provide a minimal stand in when
the library is not installed.  Each test contains detailed comments explaining
its intent so future maintainers can quickly understand the behaviours being
validated.
"""

import importlib
import sys
from types import SimpleNamespace

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# ``utils_module`` reloads ``utils.py``. If spaCy is missing we provide a simple
# stand in implementation so the similarity helper can still be exercised.
# The dummy classes mimic the minimal behaviour used by the utility functions.
@pytest.fixture()
def utils_module(monkeypatch):
    # Provide a dummy ``ipdb`` module to satisfy imports in the target modules.
    monkeypatch.setitem(sys.modules, "ipdb", SimpleNamespace(set_trace=lambda: None))
    if importlib.util.find_spec("spacy") is None:
        class DummyToken:
            def __init__(self, text, pos_="NOUN", is_stop=False):
                self.text = text
                self.pos_ = pos_
                self.is_stop = is_stop
            def __str__(self):
                return self.text
        class DummyDoc:
            def __init__(self, tokens):
                self.tokens = tokens
            def __iter__(self):
                return iter(self.tokens)
            def __len__(self):
                return len(self.tokens)
            def similarity(self, other):
                set1 = {t.text for t in self.tokens}
                set2 = {t.text for t in other.tokens}
                return len(set1 & set2) / len(set1 | set2)
        class DummyNLP:
            def __call__(self, text):
                tokens = [DummyToken(t) for t in text.split()]
                return DummyDoc(tokens)
        monkeypatch.setitem(sys.modules, "spacy", SimpleNamespace(load=lambda _: DummyNLP()))
    module = importlib.reload(
        importlib.import_module("coauthor_interface.thought_toolkit.utils")
    )
    return module


@pytest.fixture()
def parser_helper_module(utils_module):
    """Reload ``parser_helper`` after the utils fixture has patched spaCy."""
    module = importlib.reload(
        importlib.import_module("coauthor_interface.thought_toolkit.parser_helper")
    )
    return module


@pytest.fixture()
def helper_module(utils_module):
    """Reload ``helper`` once ``utils`` has been imported."""
    module = importlib.reload(
        importlib.import_module("coauthor_interface.thought_toolkit.helper")
    )
    return module


def test_sent_tokenize(utils_module):
    """Verify that ``sent_tokenize`` splits text on punctuation."""

    # The input string contains three sentences ending in different
    # punctuation marks.  The function should return them as a list of
    # individual strings without modifying their terminators.
    text = "First sentence. Second one! Third?"

    assert utils_module.sent_tokenize(text) == [
        "First sentence.",
        "Second one!",
        "Third?",
    ]


def test_timestamp_conversions_and_serializer(utils_module):
    """Round trip timestamp helpers and verify ``custom_serializer``."""

    # Choose an arbitrary millisecond timestamp and convert it back and forth
    # between ``datetime`` and string representations.
    ts_ms = 1_600_000_000_000
    dt = utils_module.get_timestamp(ts_ms)
    s = utils_module.convert_timestamp_to_string(dt)

    # Converting the string back should yield the original ``datetime``
    assert utils_module.convert_string_to_timestamp(s) == dt

    # ``custom_serializer`` should handle ``datetime`` objects and raise for
    # unknown types.
    assert utils_module.custom_serializer(dt) == dt.isoformat()
    with pytest.raises(TypeError):
        utils_module.custom_serializer(object())


def test_get_spacy_similarity(utils_module):
    """``get_spacy_similarity`` returns a normalised score between 0 and 1."""

    sim = utils_module.get_spacy_similarity("apple banana", "banana dog")

    # The exact value depends on the spaCy model, but the function should always
    # return a score within the valid [0, 1] range.
    assert 0 <= sim <= 1


def test_apply_text_operations_parser_helper(parser_helper_module):
    """Applying a sequence of ops should transform text and mask correctly."""

    doc, mask = parser_helper_module.apply_text_operations(
        "Hello",
        "AAAAA",
        [{"retain": 5}, {"insert": " world"}, {"delete": 3}],
        "user",
    )

    # After inserting ``" world"`` and deleting the last three characters the
    # text should end with ``"wo"`` and user insertions are marked with ``_`` in
    # the mask.
    assert doc == "Hello wo"
    assert mask == "AAAAA___"


def test_apply_logs_to_writing_parser_helper(parser_helper_module):
    """Processing a list of logs should mutate the document accordingly."""

    # Two logs: one inserts text and the second deletes characters.  The helper
    # applies them sequentially to the initial document and mask.
    logs = [
        {"eventSource": "user", "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]}},
        {"eventSource": "user", "textDelta": {"ops": [{"delete": 3}]}}
    ]

    writing, mask = parser_helper_module.apply_logs_to_writing("Hello", "AAAAA", logs)

    # "Hello" -> retain five characters, insert " world" and then delete last
    # three resulting characters.
    assert writing == "lo world"
    assert mask == "AA______"


def test_convert_last_action_to_complete_action(parser_helper_module):
    """Ensure helper populates extra fields from the last log entry."""

    last_action = {
        "action_logs": [{"eventTimestamp": 1000}],
        "delta_at_save": "delta",
        "writing_at_save": "text",
        "mask_at_save": "mask",
    }

    action = parser_helper_module.convert_last_action_to_complete_action(last_action)

    # The returned action should include fields copied from ``last_action`` as
    # well as ``action_end_time`` calculated from ``action_logs``.
    assert action["action_delta"] == "delta"
    assert action["action_end_writing"] == "text"
    assert action["action_end_mask"] == "mask"
    assert "action_end_time" in action


def test_get_action_type_from_log(parser_helper_module):
    """Map raw log dictionaries to an action type and modification flag."""

    # An API suggestion event should be recognised as ``present_suggestion`` and
    # not modify the text.
    log = {"eventSource": "api", "eventName": "suggestion-open"}
    assert parser_helper_module.get_action_type_from_log(log) == (
        "present_suggestion",
        False,
    )

    # A user text insertion event should map to ``insert_text`` and indicate
    # that writing has changed.
    log = {
        "eventSource": "user",
        "eventName": "text-insert",
        "textDelta": {"ops": []},
    }
    assert parser_helper_module.get_action_type_from_log(log) == (
        "insert_text",
        True,
    )


def test_extract_and_clean_text_modifications_from_action(parser_helper_module):
    """Collapse log operations into a concise description."""

    # Case 1: an insertion after retaining five characters.  The helper should
    # classify this as an INSERT operation and provide counts for the inserted
    # text.
    logs = [
        {"eventSource": "user", "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]}},
    ]
    result = parser_helper_module.extract_and_clean_text_modifications_from_action(
        "Hello",
        logs,
        "insert_text",
    )
    assert result == ("INSERT", " world", 6, 1)

    # Case 2: deletion of three characters after retaining two.  The helper
    # returns DELETE with the text removed.
    logs = [
        {"eventSource": "user", "textDelta": {"ops": [{"retain": 2}, {"delete": 3}]}}
    ]
    result = parser_helper_module.extract_and_clean_text_modifications_from_action(
        "Hello",
        logs,
        "delete_text",
    )
    assert result == ("DELETE", "llo", 3, 1)


def test_helper_apply_text_operations(helper_module):
    """The lightweight ``helper`` module mirrors ``parser_helper`` behaviour."""

    text, mask = helper_module.apply_text_operations(
        "Hello",
        "AAAAA",
        [{"retain": 5}, {"insert": " world"}, {"delete": 3}],
        "user",
    )

    # Operations are identical to the earlier parser_helper test.
    assert text == "Hello wo"
    assert mask == "AAAAA___"


def test_helper_apply_logs_to_writing(helper_module):
    """Wrapper over ``apply_text_operations`` should produce the same result."""

    logs = [
        {"eventSource": "user", "textDelta": {"ops": [{"retain": 5}, {"insert": " world"}]}},
        {"eventSource": "user", "textDelta": {"ops": [{"delete": 3}]}}
    ]

    text, mask = helper_module.apply_logs_to_writing("Hello", "AAAAA", logs)

    assert text == "lo world"
    assert mask == "AA______"
