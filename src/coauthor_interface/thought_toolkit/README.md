# Thought Toolkit

A modular toolkit for analyzing and interpreting collaborative writing/co-authoring logs. The toolkit parses raw logs into structured actions, applies semantic and behavioral analysis, and supports extensible plugin-based detection of higher-level writing patterns.

## Package Structure

- **PluginInterface.py**: Defines the abstract base class and data structures for plugins. All plugins must implement this interface.
- **level_3_plugins.py**: Example and built-in plugins for advanced (level 3) action detection.
- **active_plugins.py**: List of currently active plugins used in analysis.
- **parser_all_levels.py**: Main logic for parsing logs into actions at multiple levels (syntactic, semantic, behavioral).
- **level_2_comparisons.py, level_3_comparisons.py**: Helper functions for semantic and behavioral comparisons.
- **utils.py**: Utility functions (e.g., sentence tokenization, similarity computation).
- **run_post_session_analysis.py**: Script to process logs and output structured JSON analyses.
- **action_parser.py, parser_helper.py, helper.py**: Additional parsing and helper logic.

## Implementing a Plugin

Plugins must inherit from the `Plugin` abstract base class in `PluginInterface.py`. Each plugin must implement three static methods:

- `get_plugin_name() -> str`: Returns a unique name for the plugin.
- `detection_detected(action) -> bool`: Returns True if the plugin detects its pattern in the given action (modifies the action dict as needed).
- `intervention_action() -> Intervention`: Returns an `Intervention` instance describing what to do if the pattern is detected.

**Plugin Interface Example:**

```python
from coauthor_interface.thought_toolkit.PluginInterface import Plugin, Intervention, InterventionEnum

class MyCustomPlugin(Plugin):
    @staticmethod
    def get_plugin_name() -> str:
        return "my_custom_plugin"

    @staticmethod
    def detection_detected(action) -> bool:
        # Custom detection logic
        if action.get("level_1_action_type") == "insert_text" and "special" in action.get("action_delta", []):
            action["level_3_action_type"] = "my_custom_plugin"
            return True
        return False

    @staticmethod
    def intervention_action() -> Intervention:
        return Intervention(
            intervention_type=InterventionEnum.TOAST,
            intervention_message="Custom pattern detected!"
        )
```

**Registering Your Plugin:**

Add your plugin to the `ACTIVE_PLUGINS` list in `active_plugins.py` in order of importance:

```python
from coauthor_interface.thought_toolkit.level_3_plugins import MyCustomPlugin

ACTIVE_PLUGINS = [
    MyCustomPlugin(),
    # ... other plugins ...
]
```

## Using `run_post_session_analysis.py`

This script processes a JSON log file and outputs structured analyses at multiple levels.

### Input
- **Input file**: A JSON file mapping session IDs to lists of raw log dictionaries. Each log should contain fields like `eventSource`, `eventName`, `eventTimestamp`, and optionally `textDelta`.
- **Example input path**: `raw_keylogs_for_analysis.json` (see script for expected structure).

### Output
The script generates four JSON files in the specified output directory:

- `level_1_actions_per_session.json`: Parsed level 1 actions (syntactic/logical actions).
- `level_2_actions_per_session.json`: Level 2 actions (semantic/coordination analysis).
- `level_3_actions_per_session.json`: Level 3 actions (advanced patterns, plugin detections).
- `action_type_with_priority_per_session.json`: Actions with plugin-prioritized action types.

### Example Usage

```bash
uv run python run_post_session_analysis.py
```

By default, this will process `raw_keylogs_for_analysis.json` in the same directory and write outputs to an `output/` folder.

To process a custom file:

```python
from pathlib import Path
from coauthor_interface.thought_toolkit.run_post_session_analysis import process_logs

input_file = Path("/path/to/your/logs.json")
output_dir = Path("/path/to/output/")
process_logs(input_file, output_dir)
```

## Extending the Toolkit
- Add new plugins for custom behavioral or semantic patterns.
- Adjust the parser logic for new log formats or action types.

---

For more details, see the docstrings in each file and the example plugins in `level_3_plugins.py`. 