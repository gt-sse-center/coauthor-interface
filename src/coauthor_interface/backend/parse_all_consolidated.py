import os
import json
from tqdm import tqdm


from coauthor_interface.thought_toolkit.utils import (
    custom_serializer,
    get_spacy_similarity,
)

from coauthor_interface.thought_toolkit.parser_all_levels import (
    SameSentenceMergeAnalyzer,
    parse_level_2_actions,
    parse_level_3_actions,
)


# Load the raw log JSON file to be parsed and analyzed.
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "coauthor_logs_by_session.json")
with open(file_path) as f:
    coauthor_logs_by_session = json.load(f)


level_1_actions_per_session = {}

for session in tqdm(coauthor_logs_by_session):
    actions_analyzer = SameSentenceMergeAnalyzer(last_action=None, raw_logs=coauthor_logs_by_session[session])

    # actions_analyzer = TinyDeleteMergeAnalyzer(
    #     last_action=None,
    #     raw_logs=coauthor_logs_by_session[session]
    # )

    actions_lst, last_action = actions_analyzer.parse_actions_from_logs(
        all_logs=coauthor_logs_by_session[session], last_action=None
    )

    level_1_actions_per_session[session] = actions_lst

# Add a 'level_1_action_type' key to each action for further classification.
for session_key, actions in level_1_actions_per_session.items():
    for action in actions:
        action["level_1_action_type"] = action["action_type"]

# Save the parsed output to a JSON file in the same directory.
# The file is named 'level_1_actions_per_session.json' and contains the structured
# actions organized by session.
output_file = os.path.join(script_dir, "level_1_actions_per_session.json")
with open(output_file, "w") as f:
    json.dump(level_1_actions_per_session, f, default=custom_serializer)


# Parse level 2 actions and compute metrics for each session.
level_2_actions_per_session = parse_level_2_actions(
    level_1_actions_per_session, similarity_fcn=get_spacy_similarity
)

# Save the parsed output to a JSON file in the same directory.
# The file is named 'level_2_actions_per_session.json' and contains the structured
# actions organized by session.
output_file = os.path.join(script_dir, "level_2_actions_per_session.json")
with open(output_file, "w") as f:
    json.dump(level_2_actions_per_session, f, default=custom_serializer)


# Parse level 3 actions and compute additional metrics for each session.
level_3_actions_per_session = parse_level_3_actions(
    level_2_actions_per_session, similarity_fcn=get_spacy_similarity
)

# Save the parsed output to a JSON file in the same directory.
# The file is named 'level_3_actions_per_session.json' and contains the structured
# actions organized by session.
output_file = os.path.join(script_dir, "level_3_actions_per_session.json")
with open(output_file, "w") as f:
    json.dump(level_3_actions_per_session, f, default=custom_serializer)


# Optional step after completing all parsing steps above.
# This step involves:
# - Extracting unique action types from a specified level (e.g., 'level_3_action_type') for prioritization.
# - Defining a custom priority list to control the sorting and assignment of action types.
# - Assigning a prioritized 'action_type' to each action based on the provided priority list.
def populate_priority_list(actions_dict, level):
    """Generates a list of unique action types from a specific level in the actions dictionary."""
    priority_set = set()
    for _, actions in actions_dict.items():
        for action in actions:
            if level in action:
                priority_set.add(action[level])
    return list(priority_set)


def action_type_priority_sort(priority_list, actions_dict):
    """Sorts and assigns action types in the actions dictionary based on a predefined priority list."""
    for _, actions in actions_dict.items():
        for action in actions:
            # Iterate through the priority list and match against all levels
            for priority_action in priority_list:
                if (
                    action.get("level_1_action_type") == priority_action
                    or action.get("level_2_action_type") == priority_action
                    or action.get("level_3_action_type") == priority_action
                ):
                    action["action_type"] = priority_action
                    break
    return actions_dict


# Example usage 1: Generate a priority list of all action types from level 3 actions.
# This extracts unique 'level_3_action_type' values for prioritization and sorting.
level_3_priority_list = populate_priority_list(level_3_actions_per_session, level="level_3_action_type")

# Example usage 2: Define a custom priority list to explicitly control the sorting order of actions.
# The custom priority list takes precedence and is used to sort actions based on importance.
custom_priority_list = ["minor_insert_mindless_edit", "major_insert_major_semantic_diff"]

# Choose the custom priority list for sorting.
# Iterate through actions, match their types to the custom priority list, and assign a new 'action_type'.
action_type_with_priority_per_session = action_type_priority_sort(
    custom_priority_list, level_3_actions_per_session
)

# Save the sorted actions with prioritized types to a JSON file.
# The output file 'action_type_with_priority_per_session.json' contains actions
# with their types reassigned based on the custom priority list.
output_file = os.path.join(script_dir, "action_type_with_priority_per_session.json")
with open(output_file, "w") as f:
    json.dump(action_type_with_priority_per_session, f, default=custom_serializer)

# After running the entire Python file, you will generate four different JSON files:
# 1. 'level_1_actions_per_session.json' - Contains the parsed level 1 actions organized by session.
# 2. 'level_2_actions_per_session.json' - Builds upon level 1 actions, adding semantic differences and coordination scores.
# 3. 'level_3_actions_per_session.json' - Adds advanced interpretations, such as topic shifts and mindless edits or echoes.
# 4. 'action_type_with_priority_per_session.json' - Applies priority-based sorting to action types for refined analysis.
