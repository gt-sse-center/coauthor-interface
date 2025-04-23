# Annotated Action Schema Documentation

This schema captures metadata related to a user's text editing action in a writing interface.

---

## Top-Level Fields

| Field                     | Type                 | Description |
|---------------------------|----------------------|-------------|
| `action_type`             | `str`                | Type of level 1 action performed (e.g., `"insert_text"`). |
| `action_source`           | `str`                | Source of the action (e.g., `"user"`). |
| `action_start_log_id`     | `int`                | Log ID at the start of the action. |
| `action_start_time`       | `str` (timestamp)    | Timestamp when the action started. |
| `action_end_time`         | `str` (timestamp)    | Timestamp when the action ended. |
| `action_end_writing`      | `str`                | Final state of the text on the user's screen after the action. |
| `writing_modified`        | `bool`               | Indicates if the writing was modified during this action. *(Possibly legacy)* |
| `action_delta`            | `tuple`              | Describes the textual change: <br> - `"INSERT"` or `"DELETE"` <br> - `str`: the text that was inserted/deleted <br> - `int`: character count <br> - `int`: word count |
| `action_modified_sentences` | `list[str]`        | List of modified sentences by the action (newest version). |
| `sentences_temporal_order` | `list[str]`         | Modified sentences in the order they were modified. |

---

## Level 2 Metadata

| Field                     | Type                 | Description |
|---------------------------|----------------------|-------------|
| `level_2_info`            | `dict`               | Additional context around the edit:<br> - `select_sents_before_action`: `list[str]`<br> - `select_sents_after_action`: `list[str]` |
| `level_2_action_type`     | `str`                | Semantic category of the action (e.g., `"major_insert_major_semantic_diff"`). |
| `action_semantic_expansion` | `float`           | Degree of semantic expansion from this action. |
| `cumulative_semantic_expansion` | `float`      | Total semantic expansion up to this point. |
| `coordination_score`      | `list[float, str]`   | Coordination rating and annotation (e.g., `[0, "human reflects AI"]`). |

---

## Level 3 Metadata

| Field                     | Type                 | Description |
|---------------------------|----------------------|-------------|
| `level_3_action_type`     | `str`                | Plugin or rule name that classified this action (e.g., `"mindless_edit"`). |
| `level_3_info`            | `dict`               | Arbitrary plugin-specific metadata. |

---

## Topic Metadata

| Field                     | Type                 | Description |
|---------------------------|----------------------|-------------|
| `topic_shift`             | `tuple[bool, int]`   | Indicates topic change:<br> - `bool`: Did the topic shift?<br> - `int`: Current topic number. |

---

## Miscellaneous

| Field                     | Type                 | Description |
|---------------------------|----------------------|-------------|
| `Other`                   | `str`                | Any other notes or metadata not captured by the main schema. |