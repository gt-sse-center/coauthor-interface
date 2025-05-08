import spacy

from coauthor_interface.thought_toolkit.utils import get_spacy_similarity, sent_tokenize

nlp = spacy.load("en_core_web_md")


MIN_INSERT_WORD_COUNT = 10
MAJOR_INSRT_MAX_SIMILARITY = 0.9
MINOR_INSRT_MAX_SIMILARITY = 0.95
MAX_SIMILARITY = 0.95


def compute_expansion(writing_prev, writing_curr, modified_sents_count):
    if modified_sents_count == 0:
        return 0
    return 1 - (get_spacy_similarity(writing_prev, writing_curr)) / modified_sents_count


def get_action_expansion(action):
    modified_sents_count = len(action["action_modified_sentences"])
    if modified_sents_count > 0:
        prev_writing = action.get("action_start_writing", "")
        curr_writing = action.get("action_end_writing", "")
        return compute_expansion(prev_writing, curr_writing, modified_sents_count)
    else:
        return 0


def get_similarity_with_prev_writing_for_level_2(action, prev_writing, similarity_fcn):
    prev_sents = sent_tokenize(prev_writing)
    curr_sents = sent_tokenize(action["action_end_writing"])
    select_sents_after_action = action["action_modified_sentences"]
    select_sents_before_action = []
    for sent in prev_sents:
        if sent not in curr_sents:
            select_sents_before_action.append(sent)
    similarity = abs(
        similarity_fcn(" ".join(select_sents_after_action), " ".join(select_sents_before_action))
    )
    return similarity, {
        "select_sents_before_action": select_sents_before_action,
        "select_sents_after_action": select_sents_after_action,
    }


def parse_level_2_major_insert_major_semantic_diff(
    action,
    prev_writing_similarity,
    MIN_INSERT_WORD_COUNT=MIN_INSERT_WORD_COUNT,
    MAJOR_INSRT_MAX_SIMILARITY=MAJOR_INSRT_MAX_SIMILARITY,
):
    if (
        action["action_type"] == "insert_text"
        and action["action_delta"] != ""
        and action["action_delta"][-1] >= MIN_INSERT_WORD_COUNT
    ):
        return prev_writing_similarity <= MAJOR_INSRT_MAX_SIMILARITY
    return False


def parse_level_2_major_insert_minor_semantic_diff(
    action,
    prev_writing_similarity,
    MIN_INSERT_WORD_COUNT=MIN_INSERT_WORD_COUNT,
    MAJOR_INSRT_MAX_SIMILARITY=MAJOR_INSRT_MAX_SIMILARITY,
):
    if (
        action["action_type"] == "insert_text"
        and action["action_delta"] != ""
        and action["action_delta"][-1] >= MIN_INSERT_WORD_COUNT
    ):
        return prev_writing_similarity > MAJOR_INSRT_MAX_SIMILARITY
    return False


def parse_level_2_minor_insert_major_semantic_diff(
    action,
    prev_writing_similarity,
    MIN_INSERT_WORD_COUNT=MIN_INSERT_WORD_COUNT,
    MINOR_INSRT_MAX_SIMILARITY=MINOR_INSRT_MAX_SIMILARITY,
):
    if (
        action["action_type"] == "insert_text"
        and action["action_delta"] != ""
        and action["action_delta"][-1] < MIN_INSERT_WORD_COUNT
    ):
        return prev_writing_similarity <= MINOR_INSRT_MAX_SIMILARITY
    return False


def parse_level_2_minor_insert_minor_semantic_diff(
    action,
    prev_writing_similarity,
    MIN_INSERT_WORD_COUNT=MIN_INSERT_WORD_COUNT,
    MINOR_INSRT_MAX_SIMILARITY=MINOR_INSRT_MAX_SIMILARITY,
):
    if (
        action["action_type"] == "insert_text"
        and action["action_delta"] != ""
        and action["action_delta"][-1] < MIN_INSERT_WORD_COUNT
    ):
        return prev_writing_similarity > MINOR_INSRT_MAX_SIMILARITY
    return False


def parse_level_2_delete_major_semantic_diff(action, prev_writing_similarity, MAX_SIMILARITY=MAX_SIMILARITY):
    if action["action_type"] == "delete_text" and action["action_delta"] != "":
        return prev_writing_similarity <= MAX_SIMILARITY
    return False


def parse_level_2_delete_minor_semantic_diff(action, prev_writing_similarity, MAX_SIMILARITY=MAX_SIMILARITY):
    if action["action_type"] == "delete_text" and action["action_delta"] != "":
        return prev_writing_similarity > MAX_SIMILARITY
    return False


def find_last_major_insert_action(actions):
    for action in reversed(actions):
        if "level_2_action_type" in action and "major_insert" in action["level_2_action_type"]:
            return action
    return None


def find_last_ai_insert_suggestion(actions):
    for action in reversed(actions):
        if action.get("action_type") == "insert_suggestion":
            return action
    return None


def get_coordination_scores(action, similarity_fcn, previous_actions):
    action_start_writing = action.get("action_start_writing", "")

    action_type = action.get("action_type", "")
    level_2_action_type = action.get("level_2_action_type", "")
    action_delta = action.get("action_delta", None)

    # Handle AI-to-human coordination
    if action_type == "insert_suggestion" and action_delta:
        ai_inserted_text = action_delta[1]
        last_major_insert_action = find_last_major_insert_action(previous_actions)
        if last_major_insert_action and last_major_insert_action.get("action_delta"):
            human_inserted_text = last_major_insert_action["action_delta"][1]
            score = similarity_fcn(human_inserted_text, ai_inserted_text)
            return [score, "AI reflects human"]

    # Handle human-to-AI coordination
    if level_2_action_type and "major_insert" in level_2_action_type:
        last_ai_action = find_last_ai_insert_suggestion(previous_actions)
        if last_ai_action and last_ai_action.get("action_delta"):
            ai_inserted_text = last_ai_action["action_delta"][1]
            score = similarity_fcn(ai_inserted_text, action_start_writing)
            return [score, "human reflects AI"]

    return None
