from coauthor_interface.thought_toolkit.PluginInterface import (
    Intervention,
    InterventionEnum,
    Plugin,
)
from coauthor_interface.thought_toolkit.level_3_comparisons import (
    get_mindless_echo_after_AI,
    get_mindless_edit_of_AI,
)
from coauthor_interface.thought_toolkit.utils import get_spacy_similarity


class MajorInsertMindlessEchoPlugin(Plugin):
    @staticmethod
    def get_plugin_name() -> str:
        return "major_insert_mindless_echo"

    @staticmethod
    def detection_detected(action) -> bool:
        action_parsed = False
        if action.get("level_1_action_type") == "insert_text":
            latest_accepted_suggestion = action.get("action_delta")[1]

            # Check for major_insert_mindless_echo
            echo_bool, echo_similarity, echo_details = get_mindless_echo_after_AI(
                action, latest_accepted_suggestion, similarity_fcn=get_spacy_similarity
            )
            if echo_similarity is not None:
                action["level_3_info"] = {
                    **echo_details,
                    "similarity": echo_similarity,
                }
            if echo_bool:
                action["level_3_action_type"] = "major_insert_mindless_echo"
                action_parsed = True
        # return action
        return action_parsed

    @staticmethod
    def intervention_action() -> Intervention:
        return Intervention(
            intervention_type=InterventionEnum.TOAST,
            intervention_message="Detected a major insert mindless echo",
        )


class MinorInsertMindlessEditPlugin(Plugin):
    @staticmethod
    def get_plugin_name() -> str:
        return "minor_insert_mindless_edit"

    @staticmethod
    def detection_detected(action) -> bool:
        action_parsed = False
        if action.get("level_1_action_type") == "insert_text":
            latest_accepted_suggestion = action.get("action_delta")[1]
            edit_bool, edit_similarity, edit_details = get_mindless_edit_of_AI(
                action, latest_accepted_suggestion, similarity_fcn=get_spacy_similarity
            )
            if edit_similarity is not None:
                action["level_3_info"] = {
                    **edit_details,
                    "similarity": edit_similarity,
                }
            if edit_bool:
                action["level_3_action_type"] = "minor_insert_mindless_edit"
                action_parsed = True

        return action_parsed

    @staticmethod
    def intervention_action() -> Intervention:
        return Intervention(
            intervention_type=InterventionEnum.TOAST,
            intervention_message="Detected a minor insert mindless edit",
        )


class AnyInsert(Plugin):
    @staticmethod
    def get_plugin_name() -> str:
        return "any_insert"

    @staticmethod
    def detection_detected(action) -> bool:
        return action.get("level_1_action_type") == "insert_text"

    @staticmethod
    def intervention_action() -> Intervention:
        return Intervention(
            intervention_type=InterventionEnum.TOAST,
            intervention_message="Detected a text insertion",
        )
