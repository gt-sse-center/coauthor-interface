# ruff: disable=F405

import difflib

from coauthor_interface.thought_toolkit.helper import apply_logs_to_writing
from coauthor_interface.thought_toolkit.level_2_comparisons import (
    get_action_expansion,
    get_coordination_scores,
    get_similarity_with_prev_writing_for_level_2,
    parse_level_2_major_insert_major_semantic_diff,
    parse_level_2_major_insert_minor_semantic_diff,
    parse_level_2_minor_insert_major_semantic_diff,
    parse_level_2_minor_insert_minor_semantic_diff,
    parse_level_2_delete_major_semantic_diff,
    parse_level_2_delete_minor_semantic_diff,
)
from coauthor_interface.thought_toolkit.level_3_comparisons import (
    get_idea_alignment_order_on_AI,
    get_idea_alignment_order_on_minor_insert,
    IDEA_ALIGNMENT_MIN_WORD_COUNT,
)
from coauthor_interface.thought_toolkit.utils import (
    convert_string_to_timestamp,
    convert_timestamp_to_string,
    get_timestamp,
    sent_tokenize,
)

from coauthor_interface.thought_toolkit.active_plugins import ACTIVE_PLUGINS

########################


# Level 1: Parse the raw logs into a structured format for further analysis.
# This process includes merging individual action logs (e.g., inserting or deleting
# single letters) into cohesive words and sentences while tracking modified sentences.
class ActionsParserAnalyzer:
    """Main class for parsing and analyzing sub-turn actions."""

    def __init__(self, last_action, raw_logs=None, actions_list=None):
        """Initialize the analyzer with either a raw log list or an actions list."""
        if raw_logs is None:
            assert actions_list is not None and last_action is not None
            latest_action = self.convert_last_action_to_complete_action(last_action)
            actions_list.append(latest_action)
            self.actions_lst = actions_list
            self.last_action = last_action
            self.analyzer_on = True
        else:
            self.actions_lst, self.last_action = self.parse_actions_from_logs(raw_logs, last_action)
            self.analyzer_on = False

    def parse_actions_from_logs(self, all_logs, last_action=None):
        raise NotImplementedError("Subclasses must implement this method")

    def convert_last_action_to_complete_action(self, last_action):
        """Converts the last action into a complete action for live analysis."""
        # Create a shallow copy of the last_action dictionary
        action = last_action.copy()

        # Modify only the necessary keys
        action["action_end_time"] = convert_timestamp_to_string(
            get_timestamp(last_action["action_logs"][-1]["eventTimestamp"])
        )
        action["action_delta"] = last_action["delta_at_save"]
        action["action_end_writing"] = last_action["writing_at_save"]
        action["action_end_mask"] = last_action["mask_at_save"]

        return action

    def update_sentences(self, current_writing, sentences_seen_so_far):
        """Updates sentences_seen_so_far and returns sentences_temporal_order."""
        action_modified_sentences = []
        current_sentences = {}
        for sent in sent_tokenize(current_writing):
            sent = sent.strip()
            if sent:
                if sent not in sentences_seen_so_far:
                    sentences_seen_so_far[sent] = len(sentences_seen_so_far)
                    action_modified_sentences.append(sent)
                current_sentences[sent] = sentences_seen_so_far[sent]
        sentences_temporal_order = [tup[0] for tup in sorted(current_sentences.items(), key=lambda t: t[1])]
        return action_modified_sentences, sentences_temporal_order

    def get_action_type_from_log(self, log):
        """Processes and analyzes logs related to text modifications."""
        action_type = None
        writing_was_modified = False
        if log["eventSource"] == "api":
            if (
                log["eventName"] == "suggestion-open"
                or log["eventName"] == "suggestion-reopen"
                or log["eventName"] == "suggestion-close"
                or log["eventName"] in ["cursor-forward", "cursor-backward", "cursor-select"]
            ):
                action_type = "present_suggestion"
            elif log["eventName"] == "text-insert":
                action_type = "insert_suggestion"
            else:
                print(f"Error: {log}")
        elif log["eventSource"] == "user":
            if log["eventName"] == "suggestion-get":
                action_type = "query_suggestion"
            elif log["eventName"] in [
                "suggestion-hover",
                "suggestion-up",
                "suggestion-down",
            ]:
                action_type = "hover_over_text"
            elif log["eventName"] == "suggestion-select":
                action_type = "accept_suggestion"
            elif log["eventName"] == "suggestion-close":
                action_type = "reject_suggestion"
            elif log["eventName"] == "suggestion-reopen":
                action_type = "present_suggestion"
            elif log["eventName"] in [
                "cursor-select",
                "cursor-forward",
                "cursor-backward",
            ]:
                action_type = "cursor_operation"
            elif log["eventName"] == "text-insert":
                action_type = "insert_text"
            elif log["eventName"] == "text-delete":
                action_type = "delete_text"
            else:
                print(f"Error: {log}")
        else:
            print(f"Error: {log}")
        if "textDelta" in log and "ops" in log["textDelta"]:
            writing_was_modified = True
        if action_type is None:
            print(log["eventName"])
        return action_type, writing_was_modified

    def extract_and_clean_text_modifications_from_action(
        self, writing_at_start_of_action, current_logs, current_action
    ):
        """
        Extracts and organizes text modifications from a series of logs into
        meaningful operations like INSERT or DELETE.
        """
        original_text = writing_at_start_of_action
        new_text = ""
        insert_string = ""
        insert_char_count = 0
        delete_string = ""
        delete_char_count = 0

        for log in current_logs:
            if "textDelta" in log and "ops" in log["textDelta"]:
                ops = log["textDelta"]["ops"]
                source = log["eventSource"]
                for op in ops:
                    if "retain" in op:
                        num_char = op["retain"]
                        retain_text = original_text[:num_char]
                        original_text = original_text[num_char:]
                        new_text = new_text + retain_text
                    if "insert" in op:
                        insert_text = op["insert"]
                        insert_char_count += len(insert_text)
                        new_text = new_text + insert_text
                        insert_string = insert_string + insert_text
                    if "delete" in op:
                        num_char = op["delete"]
                        delete_char_count += num_char
                        if original_text:
                            delete_string = original_text[:num_char] + delete_string
                            original_text = original_text[num_char:]
                        else:
                            delete_string = new_text[-num_char:] + delete_string
                            new_text = new_text[:-num_char]
                            insert_string = insert_string[:-num_char]

        if current_action in ["insert_text", "insert_suggestion"]:
            return (
                "INSERT",
                insert_string,
                len(insert_string),
                len(insert_string.split()),
            )
        elif current_action in ["delete_text", "TBD"]:
            return (
                "DELETE",
                delete_string,
                len(delete_string),
                len(delete_string.split()),
            )
        else:
            return ""

    def action_modification_sentence_tracker(self, old_text, new_text):
        """
        Compares sentences in the old and new versions of text to detect modifications
        at the sentence level.
        """
        old_sentences = sent_tokenize(old_text)
        new_sentences = sent_tokenize(new_text)

        matcher = difflib.SequenceMatcher(None, old_sentences, new_sentences)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                if tag == "insert" or tag == "delete":
                    return False
                elif tag == "replace":
                    changes.extend(zip(old_sentences[i1:i2], new_sentences[j1:j2]))

        if not changes:
            return True

        if len(changes) == 1:
            return True
        return False


class SameSentenceMergeAnalyzer(ActionsParserAnalyzer):
    """
    Parses a list of logs into structured actions. It merges insertions and deletions
    occurring within the same sentence into a single insertion operation.
    - Merges insertions/deletions within the same sentence into a single action.
    - Separately handles suggestion-related operations and large deletions.
    """

    SUGGESTION_ACTIONS = [
        "present_suggestion",
        "query_suggestion",
        "accept_suggestion",
        "reject_suggestion",
        "insert_suggestion",
        "hover_over_text",
    ]

    def parse_actions_from_logs(self, all_logs, last_action=None):
        """Parse actions using the same-sentence merge logic."""
        DLT_CHAR_MAX_COUNT = 9
        return self.parse_actions_same_sentence(all_logs, last_action, DLT_CHAR_MAX_COUNT)

    def parse_actions_same_sentence(self, all_logs, last_action, DLT_CHAR_MAX_COUNT):
        """Same sentence merge logic"""
        all_logs = [log for log in all_logs if log["eventName"] != "saving-word"]

        all_actions = []
        current_action = None
        current_logs = []
        current_source = None
        action_start_time = None
        action_start_log_id = None

        action_start_writing = last_action.get("action_end_writing", "") if last_action else ""
        current_writing = action_start_writing
        current_mask = last_action.get("action_end_mask", "") if last_action else ""
        sentences_seen_so_far = last_action.get("sentences_seen_so_far", {}) if last_action else {}

        last_special_action = None

        for i, log in enumerate(all_logs):
            # Determine the type of the current log action
            log_action, writing_modified = self.get_action_type_from_log(log)
            log_source = log["eventSource"]

            # Handle suggestion-related actions
            if log_action in self.SUGGESTION_ACTIONS:
                if log_action == last_special_action:
                    continue

                if current_action and current_logs:
                    current_writing, current_mask = self.finalize_current_action_and_append(
                        all_actions,
                        current_action,
                        current_logs,
                        action_start_time,
                        action_start_log_id,
                        action_start_writing,
                        current_writing,
                        current_mask,
                        current_source,
                        sentences_seen_so_far,
                    )

                # Handle suggestion-related operations
                action_dct, current_writing, current_mask = self.handle_suggestion_operations(
                    log_action,
                    log_source,
                    log,
                    i,
                    writing_modified,
                    current_writing,
                    current_mask,
                    sentences_seen_so_far,
                )
                all_actions.append(action_dct)
                last_special_action = log_action

                # Prepare the last_action dictionary for future calls and update based on act_dict
                last_action = self.prepare_last_action(
                    current_action=action_dct["action_type"],
                    current_source=action_dct["action_source"],
                    current_logs=action_dct["action_logs"],
                    action_start_log_id=action_dct["action_start_log_id"],
                    action_start_time=action_dct["action_start_time"],
                    action_start_writing=current_writing,
                    current_writing=current_writing,
                    current_mask=current_mask,
                    sentences_seen_so_far=sentences_seen_so_far,
                )

                # clean up - current action has been saved and appended to all_actions
                current_source = action_dct["action_source"]
                current_action = None
                current_logs = []
                action_start_time = None
                action_start_log_id = None
                action_start_writing = current_writing

                continue

            # Handle cursor operations
            if log_action == "cursor_operation":
                (
                    current_action,
                    current_source,
                    action_start_time,
                    action_start_log_id,
                    action_start_writing,
                ) = self.handle_cursor_operation(
                    current_action,
                    current_source,
                    action_start_time,
                    action_start_log_id,
                    action_start_writing,
                    current_writing,
                    log_source,
                    log,
                    i,
                )
                current_logs.append(log)
                continue

            # Process text insertions or deletions
            new_writing, new_mask, same_sentence, large_delete = self.process_text_insert_delete(
                log_action, current_writing, current_mask, log, DLT_CHAR_MAX_COUNT
            )

            # Decide whether to start a new action
            if self.check_if_start_new_action(log_action, current_action, same_sentence, large_delete):
                if current_action and current_logs:
                    current_writing, current_mask = self.finalize_current_action_and_append(
                        all_actions,
                        current_action,
                        current_logs,
                        action_start_time,
                        action_start_log_id,
                        action_start_writing,
                        current_writing,
                        current_mask,
                        current_source,
                        sentences_seen_so_far,
                    )

                    current_action = None
                    current_logs = []
                    action_start_time = None
                    action_start_log_id = None
                    action_start_writing = current_writing

                # Handle large deletes as separate actions
                if log_action == "delete_text" and large_delete:
                    action_dct, current_writing, current_mask = self.handle_large_delete(
                        current_writing,
                        current_mask,
                        log,
                        i,
                        log_source,
                        writing_modified,
                        sentences_seen_so_far,
                    )
                    all_actions.append(action_dct)
                    action_start_writing = current_writing
                    continue

                # Start a new insert_text action
                if log_action == "insert_text":
                    (
                        current_action,
                        current_source,
                        action_start_time,
                        action_start_log_id,
                        action_start_writing,
                        current_logs,
                        current_writing,
                        current_mask,
                    ) = self.start_new_action(
                        log_action,
                        log_source,
                        log,
                        i,
                        current_writing,
                        new_writing,
                        new_mask,
                    )
                    continue
            else:
                current_logs.append(log)
                current_writing = new_writing
                current_mask = new_mask

        if current_action and current_logs:
            current_writing, current_mask = self.finalize_current_action_and_append(
                all_actions,
                current_action,
                current_logs,
                action_start_time,
                action_start_log_id,
                action_start_writing,
                current_writing,
                current_mask,
                current_source,
                sentences_seen_so_far,
            )

            # Prepare the last_action dictionary for future calls
            last_action = self.prepare_last_action(
                current_action,
                current_source,
                current_logs,
                action_start_log_id,
                action_start_time,
                action_start_writing,
                current_writing,
                current_mask,
                sentences_seen_so_far,
            )

        return all_actions, last_action

    def finalize_current_action_and_append(
        self,
        all_actions_lst,
        current_action,
        current_logs,
        action_start_time,
        action_start_log_id,
        action_start_writing,
        current_writing,
        current_mask,
        current_source,
        sentences_seen_so_far,
    ):
        """
        Finalizes the current action and appends it to all_actions_lst. Returns updated current_writing and current_mask.
        """
        action_dct, current_writing, current_mask = self.finalize_current_action_same_sentence(
            current_action,
            current_logs,
            action_start_time,
            action_start_log_id,
            action_start_writing,
            current_writing,
            current_mask,
            current_source,
            sentences_seen_so_far,
        )
        all_actions_lst.append(action_dct)
        return current_writing, current_mask

    def handle_suggestion_operations(
        self,
        log_action,
        log_source,
        log,
        i,
        writing_modified,
        current_writing,
        current_mask,
        sentences_seen_so_far,
    ):
        """
        Handles suggestion-related operations, including insert_suggestion, present_suggestion,
        query_suggestions, accept_suggestion, reject_suggestion, hovering_operation.
        """
        if log_action == "insert_suggestion":
            delta = self.extract_and_clean_text_modifications_from_action(
                current_writing, [log], "insert_suggestion"
            )
            current_writing, current_mask = apply_logs_to_writing(current_writing, current_mask, [log])
            action_modified_sentences, sentences_temporal_order = self.update_sentences(
                current_writing, sentences_seen_so_far
            )
        else:
            delta = ""
            action_modified_sentences = []
            _, sentences_temporal_order = self.update_sentences(current_writing, sentences_seen_so_far)

        timestamp_str = convert_timestamp_to_string(get_timestamp(log["eventTimestamp"]))
        action_dct = {
            "action_type": log_action,
            "action_source": log_source,
            "action_logs": [log],
            "action_start_log_id": i,
            "action_start_time": timestamp_str,
            "action_end_time": timestamp_str,
            "action_start_writing": current_writing,
            "action_end_writing": current_writing,
            "action_end_mask": current_mask,
            "writing_modified": True,
            "action_delta": delta,
            "action_modified_sentences": action_modified_sentences,
            "sentences_temporal_order": sentences_temporal_order,
        }

        return action_dct, current_writing, current_mask

    def handle_cursor_operation(
        self,
        current_action,
        current_source,
        action_start_time,
        action_start_log_id,
        action_start_writing,
        current_writing,
        log_source,
        log,
        i,
    ):
        """
        Handles cursor_operation logs. If no current action is ongoing,
        initializes a new insert_text action context.
        """
        if current_action is None:
            current_action = "insert_text"
            current_source = log_source
            action_start_time = convert_timestamp_to_string(get_timestamp(log["eventTimestamp"]))
            action_start_log_id = i
            action_start_writing = current_writing
        return (
            current_action,
            current_source,
            action_start_time,
            action_start_log_id,
            action_start_writing,
        )

    def process_text_insert_delete(self, log_action, current_writing, current_mask, log, DLT_CHAR_MAX_COUNT):
        """
        Processes text insertions and deletions, checks if they occur within the same sentence,
        and identifies large deletes.
        """
        if log_action in ["insert_text", "delete_text"]:
            new_writing, new_mask = apply_logs_to_writing(current_writing, current_mask, [log])
            same_sentence = self.action_modification_sentence_tracker(current_writing, new_writing)
        else:
            new_writing = current_writing
            new_mask = current_mask
            same_sentence = True

        large_delete = False
        if log_action == "delete_text":
            delete_char_count = sum(op.get("delete", 0) for op in log["textDelta"]["ops"] if "delete" in op)
            large_delete = delete_char_count > DLT_CHAR_MAX_COUNT

        return new_writing, new_mask, same_sentence, large_delete

    def check_if_start_new_action(self, log_action, current_action, same_sentence, large_delete):
        """
        Determines whether to start a new action based on the current log action,
        sentence alignment, and large delete criteria.
        """
        if log_action == "delete_text":
            return large_delete or not same_sentence or current_action != "insert_text"
        if log_action == "insert_text":
            return not same_sentence
        return True

    def start_new_action(self, log_action, log_source, log, i, current_writing, new_writing, new_mask):
        """Starts a new insert_text action, initializing all relevant variables."""
        current_action = "insert_text"
        current_source = log_source
        action_start_time = convert_timestamp_to_string(get_timestamp(log["eventTimestamp"]))
        action_start_log_id = i
        action_start_writing = current_writing
        current_logs = [log]
        return (
            current_action,
            current_source,
            action_start_time,
            action_start_log_id,
            action_start_writing,
            current_logs,
            new_writing,
            new_mask,
        )

    def handle_large_delete(
        self,
        current_writing,
        current_mask,
        log,
        i,
        log_source,
        writing_modified,
        sentences_seen_so_far,
    ):
        """Handles large deletion events by creating a separate delete_text action."""
        delta = self.extract_and_clean_text_modifications_from_action(current_writing, [log], "delete_text")
        current_writing, current_mask = apply_logs_to_writing(current_writing, current_mask, [log])
        action_modified_sentences, sentences_temporal_order = self.update_sentences(
            current_writing, sentences_seen_so_far
        )

        timestamp_str = convert_timestamp_to_string(get_timestamp(log["eventTimestamp"]))
        action_dct = {
            "action_type": "delete_text",
            "action_source": log_source,
            "action_logs": [log],
            "action_start_log_id": i,
            "action_start_time": timestamp_str,
            "action_end_time": timestamp_str,
            "writing_modified": writing_modified,
            "action_delta": delta,
            "action_end_writing": current_writing,
            "action_end_mask": current_mask,
            "action_modified_sentences": action_modified_sentences,
            "sentences_temporal_order": sentences_temporal_order,
        }
        return action_dct, current_writing, current_mask

    def finalize_current_action_same_sentence(
        self,
        current_action,
        current_logs,
        action_start_time,
        action_start_log_id,
        action_start_writing,
        current_writing,
        current_mask,
        current_source,
        sentences_seen_so_far,
    ):
        """
        Finalizes the current action by extracting deltas, updating writing, and preparing the
        final action dictionary.
        """
        delta = self.extract_and_clean_text_modifications_from_action(
            action_start_writing, current_logs, current_action
        )
        if delta and delta[1].strip():
            current_writing, current_mask = apply_logs_to_writing(
                action_start_writing, current_mask, current_logs
            )

        action_modified_sentences, sentences_temporal_order = self.update_sentences(
            current_writing, sentences_seen_so_far
        )
        end_timestamp_str = convert_timestamp_to_string(get_timestamp(current_logs[-1]["eventTimestamp"]))

        action_dct = {
            "action_type": current_action,
            "action_source": current_source,
            "action_logs": current_logs,
            "action_start_log_id": action_start_log_id,
            "action_start_time": action_start_time,
            "action_start_writing": action_start_writing,
            "action_end_time": end_timestamp_str,
            "action_end_writing": current_writing,
            "action_end_mask": current_mask,
            "writing_modified": True,
            "action_delta": delta,
            "action_modified_sentences": action_modified_sentences,
            "sentences_temporal_order": sentences_temporal_order,
        }
        return action_dct, current_writing, current_mask

    def prepare_last_action(
        self,
        current_action,
        current_source,
        current_logs,
        action_start_log_id,
        action_start_time,
        action_start_writing,
        current_writing,
        current_mask,
        sentences_seen_so_far,
    ):
        """
        Prepares the last_action dictionary, representing the final state after processing all logs.
        """
        delta = ""
        if current_logs:
            delta = self.extract_and_clean_text_modifications_from_action(
                action_start_writing, current_logs, current_action
            )

        action_modified_sentences, sentences_temporal_order = self.update_sentences(
            current_writing, sentences_seen_so_far
        )

        return {
            "action_type": current_action if current_action else "",
            "action_source": current_source if current_source else "",
            "action_logs": current_logs,
            "action_start_log_id": action_start_log_id,
            "action_start_time": action_start_time,
            "action_start_writing": action_start_writing,
            "action_start_mask": current_mask,
            "writing_modified": True,
            "writing_at_save": current_writing,
            "mask_at_save": current_mask,
            "delta_at_save": delta,
            "sentences_seen_so_far": sentences_seen_so_far,
            "action_modified_sentences": action_modified_sentences,
            "sentences_temporal_order": sentences_temporal_order,
        }


class TinyDeleteMergeAnalyzer(ActionsParserAnalyzer):
    """
    Parses a list of logs into structured actions that group together log events
    of the same type. It also merges consecutive insertions if they are
    separated by tiny deletes in between.
    """

    def parse_actions_from_logs(self, all_logs, last_action=None):
        """Parse actions using the tiny delete merge logic."""
        return self.parse_actions_tiny_delete(all_logs, last_action, DLT_CHAR_MAX_COUNT=9)

    def parse_actions_tiny_delete(self, all_logs, last_action, DLT_CHAR_MAX_COUNT):
        """Tiny delete merge logic."""
        all_actions_lst = []
        all_logs = [log for log in all_logs if log["eventName"] != "saving-word"]
        if last_action is None:
            log_action, writing_modified = self.get_action_type_from_log(all_logs[0])
            assert log_action != "TBD"
            last_action = {
                "action_type": log_action,
                "action_source": all_logs[0]["eventSource"],
                "action_logs": [all_logs[0]],
                "action_start_log_id": 0,
                "action_start_time": convert_timestamp_to_string(
                    get_timestamp(all_logs[0]["eventTimestamp"])
                ),
                "action_start_writing": "",
                "action_start_mask": "",
                "writing_modified": writing_modified,
                "sentences_seen_so_far": {},
            }
        current_action = last_action["action_type"]
        current_source = last_action["action_source"]
        current_logs = last_action["action_logs"]
        current_start_time = convert_string_to_timestamp(last_action["action_start_time"])
        current_writing = last_action["action_start_writing"]
        current_mask = last_action["action_start_mask"]
        prev_writing_modified = last_action["writing_modified"]
        start_log_id = last_action["action_start_log_id"]
        action_modified_sentences = []
        sentences_temporal_order = []
        sentences_seen_so_far = last_action["sentences_seen_so_far"]
        start_id = start_log_id + len(current_logs)
        for i in range(start_id, len(all_logs)):
            log = all_logs[i]
            log_action, writing_modified = self.get_action_type_from_log(log)
            if log["eventSource"] != current_source:  # change in turn
                to_end_action = True
            elif log_action == current_action:
                to_end_action = False
            elif log_action != current_action and current_source == "api":  # change in action on API side
                to_end_action = False
                if current_action == "present_suggestion" and log_action == "insert_suggestion":
                    current_action = log_action
            elif (
                log_action != "TBD" and log_action != current_action and current_source == "user"
            ):  # change in action when no deletes are involved
                to_end_action = True
            elif log_action == "TBD" and current_action not in [
                "insert_text",
                "delete_text",
            ]:
                to_end_action = True
                log_action = "delete_text"  # first delete in an action
            elif log_action == "TBD" and current_action == "delete_text":
                to_end_action = False
                log_action = "delete_text"
            elif log_action == "TBD" and current_action == "insert_text":
                # check if small deletion would still be part of 'insert_text'
                latest_delete_logs_start_id = len(current_logs)
                delete_char_count = 0
                for j in range(len(current_logs), 0, -1):
                    if latest_delete_logs_start_id - j == 1:
                        lg = current_logs[j]
                        if lg["eventName"] == "text-delete":
                            for op_dct in lg["textDelta"]["ops"]:
                                if "delete" in op_dct:
                                    delete_char_count += op_dct["delete"]
                                    latest_delete_logs_start_id = j
                assert delete_char_count <= DLT_CHAR_MAX_COUNT
                for op_dct in log["textDelta"]["ops"]:
                    if "delete" in op_dct:
                        delete_char_count += op_dct["delete"]
                if delete_char_count > DLT_CHAR_MAX_COUNT:
                    delta = self.extract_and_clean_text_modifications_from_action(
                        current_writing,
                        current_logs[:latest_delete_logs_start_id],
                        current_action,
                    )
                    current_writing, current_mask = apply_logs_to_writing(
                        current_writing,
                        current_mask,
                        current_logs[:latest_delete_logs_start_id],
                    )
                    current_sentences = {}
                    for sent in sent_tokenize(current_writing):
                        if sent not in sentences_seen_so_far:
                            sentences_seen_so_far[sent] = len(sentences_seen_so_far)
                            action_modified_sentences.append(sent)
                        current_sentences[sent] = sentences_seen_so_far[sent]
                    sentences_temporal_order = [
                        tup[0] for tup in sorted(current_sentences.items(), key=lambda t: t[1])
                    ]
                    action_dct = {
                        "action_type": current_action,
                        "action_source": current_source,
                        "action_logs": current_logs[:latest_delete_logs_start_id],
                        "action_start_log_id": start_log_id,
                        "action_start_time": convert_timestamp_to_string(current_start_time),
                        "action_end_time": convert_timestamp_to_string(
                            get_timestamp(current_logs[latest_delete_logs_start_id - 1]["eventTimestamp"])
                        ),
                        "action_end_writing": current_writing,
                        "action_end_mask": current_mask,
                        "writing_modified": prev_writing_modified,
                        "action_delta": delta,
                        "action_modified_sentences": action_modified_sentences,
                        "sentences_temporal_order": sentences_temporal_order,
                    }
                    all_actions_lst.append(action_dct)
                    to_end_action = False
                    current_action = "delete_text"
                    assert latest_delete_logs_start_id <= len(current_logs)
                    if latest_delete_logs_start_id == len(current_logs):
                        current_logs = [log]
                    else:
                        current_logs = current_logs[latest_delete_logs_start_id:] + [log]
                    current_start_time = get_timestamp(current_logs[0]["eventTimestamp"])
                    prev_writing_modified = True
                    start_log_id += latest_delete_logs_start_id
                    action_delta = ""
                    action_modified_sentences = []
                    # sentences_temporal_order = []
                # else:
                #     to_end_action = True
                #     print('ERROR', len(current_logs), latest_delete_logs_start_id)
                else:
                    to_end_action = False
            else:
                print(f"Error: {current_action}, {log_action}, {log}")

            if to_end_action:  # end the current_action and start new action with the given log
                if prev_writing_modified:
                    delta = self.extract_and_clean_text_modifications_from_action(
                        current_writing, current_logs, current_action
                    )
                    current_writing, current_mask = apply_logs_to_writing(
                        current_writing, current_mask, current_logs
                    )
                    current_sentences = {}
                    for sent in sent_tokenize(current_writing):
                        if sent not in sentences_seen_so_far:
                            sentences_seen_so_far[sent] = len(sentences_seen_so_far)
                            action_modified_sentences.append(sent)
                        current_sentences[sent] = sentences_seen_so_far[sent]
                    sentences_temporal_order = [
                        tup[0] for tup in sorted(current_sentences.items(), key=lambda t: t[1])
                    ]

                else:
                    delta = ""
                action_dct = {
                    "action_type": current_action,
                    "action_source": current_source,
                    "action_logs": current_logs,
                    "action_start_log_id": start_log_id,
                    "action_start_time": convert_timestamp_to_string(current_start_time),
                    "action_end_time": convert_timestamp_to_string(
                        get_timestamp(current_logs[-1]["eventTimestamp"])
                    ),
                    "action_end_writing": current_writing,
                    "action_end_mask": current_mask,
                    "writing_modified": prev_writing_modified,
                    "action_delta": delta,
                    "action_modified_sentences": action_modified_sentences,
                    "sentences_temporal_order": sentences_temporal_order,
                }
                all_actions_lst.append(action_dct)

                current_action = log_action
                current_source = log["eventSource"]
                current_logs = [log]
                current_start_time = get_timestamp(log["eventTimestamp"])
                writing_modified = last_action["writing_modified"]
                start_log_id = i
                action_delta = ""
                action_modified_sentences = []
                # sentences_temporal_order = []
                to_end_action = False
            else:
                current_logs.append(log)

            if not prev_writing_modified:
                prev_writing_modified = writing_modified

        if prev_writing_modified:
            last_delta = self.extract_and_clean_text_modifications_from_action(
                current_writing, current_logs, current_action
            )
            last_writing, last_mask = apply_logs_to_writing(current_writing, current_mask, current_logs)
            last_sentences = {}
            sid = len(sentences_seen_so_far)
            for sent in sent_tokenize(last_writing):
                if sent not in sentences_seen_so_far:
                    last_sentences[sent] = sid
                    sid += 1
                    action_modified_sentences.append(sent)
                else:
                    last_sentences[sent] = sentences_seen_so_far[sent]
            sentences_temporal_order = [tup[0] for tup in sorted(last_sentences.items(), key=lambda t: t[1])]
        else:
            last_writing = current_writing
            last_mask = current_mask
            last_delta = ""

        last_action = {
            "action_type": current_action,
            "action_source": current_source,
            "action_logs": current_logs,
            "action_start_log_id": start_log_id,
            "action_start_time": convert_timestamp_to_string(current_start_time),
            "action_start_writing": current_writing,
            "action_start_mask": current_mask,
            "writing_modified": prev_writing_modified,
            "writing_at_save": last_writing,
            "mask_at_save": last_mask,
            "delta_at_save": last_delta,
            "sentences_seen_so_far": sentences_seen_so_far,
            "action_modified_sentences": action_modified_sentences,
            "sentences_temporal_order": sentences_temporal_order,
        }

        return all_actions_lst, last_action


# Level 2: Parse the level 2 actions based on level 1 actions.
# This process involves:
# - Classifying level 2 action types (e.g., major/minor insertions or deletions with semantic differences).
# - Tracking semantic expansion and computing cumulative semantic expansion.
# - Computing coordination scores to evaluate consistency and alignment between actions.
def parse_level_2_actions(level_1_actions_per_session, similarity_fcn):
    for session_key, actions_lst in level_1_actions_per_session.items():
        prev_writing = None
        cumulative_expansion = 0

        for idx, action in enumerate(actions_lst):
            action["level_2_info"] = {}

            # Compute similarity with previous writing
            if idx > 0 and "action_end_writing" in action and prev_writing:
                prev_writing_similarity, sents_info_dct = get_similarity_with_prev_writing_for_level_2(
                    action, prev_writing, similarity_fcn
                )

                action["level_2_info"]["similarity"] = prev_writing_similarity
                action["level_2_info"] = sents_info_dct

                # Determine level 2 action type based on similarity
                if parse_level_2_major_insert_major_semantic_diff(action, prev_writing_similarity):
                    action["level_2_action_type"] = "major_insert_major_semantic_diff"
                elif parse_level_2_major_insert_minor_semantic_diff(action, prev_writing_similarity):
                    action["level_2_action_type"] = "major_insert_minor_semantic_diff"
                elif parse_level_2_minor_insert_major_semantic_diff(action, prev_writing_similarity):
                    action["level_2_action_type"] = "minor_insert_major_semantic_diff"
                elif parse_level_2_minor_insert_minor_semantic_diff(action, prev_writing_similarity):
                    action["level_2_action_type"] = "minor_insert_minor_semantic_diff"

                if "delete" in action.get("action_type", ""):
                    if parse_level_2_delete_major_semantic_diff(action, prev_writing_similarity):
                        action["level_2_action_type"] = "delete_major_semantic_diff"
                    elif parse_level_2_delete_minor_semantic_diff(action, prev_writing_similarity):
                        action["level_2_action_type"] = "delete_minor_semantic_diff"

            # Compute semantic expansion for actions
            action["action_semantic_expansion"] = get_action_expansion(action)

            # Compute cumulative expansion
            cumulative_expansion += action["action_semantic_expansion"]
            action["cumulative_semantic_expansion"] = cumulative_expansion

            # Update prev_writing
            prev_writing = action.get("action_end_writing", prev_writing)

    for _, actions_lst in level_1_actions_per_session.items():
        for idx, action in enumerate(actions_lst):
            # Compute coordination scores based on previous actions
            coordination_score = get_coordination_scores(action, similarity_fcn, actions_lst[:idx])
            if coordination_score:
                action["coordination_score"] = coordination_score

    return level_1_actions_per_session


# Level 3: Parse the level 3 actions based on level 2 actions.
# This process involves:
# - Tracking the latest accepted suggestions to align with user insertions.
# - Identifying patterns like "mindless echo" and "mindless edit" of AI suggestions.
# - Detecting topic shifts and counting new ideas
def parse_level_3_actions(level_2_actions_per_session, similarity_fcn):
    for session_key, actions_lst in level_2_actions_per_session.items():
        latest_accepted_suggestion = ""
        curr_idea_sentence_list = [""]
        running_idea_count = 0

        for action in actions_lst:
            action_parsed = False

            # Track the latest accepted suggestion
            if action.get("level_1_action_type") == "insert_suggestion":
                latest_accepted_suggestion = action.get("action_delta")[1]
                curr_idea_sentence_list = get_idea_alignment_order_on_AI(
                    action, curr_idea_sentence_list, similarity_fcn
                )
                if len(curr_idea_sentence_list) == 1:  # New idea detected
                    running_idea_count += 1
                action["topic_shift"] = running_idea_count

            # Process text insert operations
            for plugin in ACTIVE_PLUGINS:
                if plugin.detection_detected(action):
                    action["level_3_action_type"] = plugin.get_plugin_name()
                    action_parsed = True
                    break

            # Handle topic shifts for text insertions
            if not action_parsed and action.get("level_1_action_type") == "insert_text":
                if action["action_delta"][-1] >= IDEA_ALIGNMENT_MIN_WORD_COUNT:
                    curr_idea_sentence_list = get_idea_alignment_order_on_AI(
                        action, curr_idea_sentence_list, similarity_fcn
                    )
                    if len(curr_idea_sentence_list) == 1:  # New idea detected
                        running_idea_count += 1
                    action["topic_shift"] = running_idea_count
                else:
                    curr_idea_sentence_list, new_idea = get_idea_alignment_order_on_minor_insert(
                        action, curr_idea_sentence_list, similarity_fcn
                    )
                    if new_idea:
                        running_idea_count += 1
                    action["topic_shift"] = running_idea_count

    return level_2_actions_per_session
