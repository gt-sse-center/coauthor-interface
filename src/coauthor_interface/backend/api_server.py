"""
Starts a Flask server that handles API requests from the frontend.
"""

import gc
import os
import random
import warnings
from argparse import ArgumentParser
from time import time

import openai
from openai import OpenAI
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

from coauthor_interface.thought_toolkit.active_plugins import ACTIVE_PLUGINS
from coauthor_interface.backend.helper import (
    append_session_to_file,
    compute_stats,
    get_config_for_log,
    get_context_window_size,
    get_last_text_from_log,
    get_uuid,
    print_current_sessions,
    print_verbose,
    retrieve_log_paths,
    save_log_to_jsonl,
    check_for_level_3_actions,
)
from coauthor_interface.backend.parsing import (
    filter_suggestions,
    parse_probability,
    parse_prompt,
    parse_modified_prompt,
    parse_suggestion,
)

from coauthor_interface.thought_toolkit.parser_all_levels import (
    SameSentenceMergeAnalyzer,
    parse_level_3_actions,
)

from coauthor_interface.thought_toolkit.parser_helper import (
    convert_last_action_to_complete_action,
)
from coauthor_interface.thought_toolkit.utils import get_spacy_similarity

from coauthor_interface.backend.reader import (
    read_access_codes,
    read_api_keys,
    read_blocklist,
    read_examples,
    read_log,
    read_prompts,
    update_metadata,
)

from coauthor_interface.thought_toolkit.PluginInterface import InterventionEnum

warnings.filterwarnings("ignore", category=FutureWarning)

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

SESSIONS = dict()
app = Flask(__name__)
CORS(app)  # For Access-Control-Allow-Origin

SUCCESS = True
FAILURE = False


@app.route("/api/start_session", methods=["POST"])
@cross_origin(origin="*")
def start_session():
    content = request.json
    result = {}

    # Read latest prompts, examples, and access codes
    # pylint: disable=possibly-used-before-assignment
    examples = read_examples(config_dir)
    prompts = read_prompts(config_dir)
    # pylint: enable=possibly-used-before-assignment
    allowed_access_codes = read_access_codes(config_dir)

    # Check access codes
    access_code = content["accessCode"]
    if access_code not in allowed_access_codes:
        if not access_code:
            access_code = "(not provided)"
        result["status"] = FAILURE
        result["message"] = f"Invalid access code: {access_code}. Please check your access code in URL."
        print_current_sessions(SESSIONS, "Invalid access code")
        return jsonify(result)

    config = allowed_access_codes[access_code]

    # Setup a new session
    session_id = get_uuid()  # Generate unique session ID
    verification_code = session_id

    # Information returned to user
    result = {
        "access_code": access_code,
        "session_id": session_id,
        "example_text": examples[config.example],
        "prompt_text": prompts[config.prompt],
    }
    result.update(config.convert_to_dict())

    # Information stored on the server
    SESSIONS[session_id] = {
        "access_code": access_code,
        "session_id": session_id,
        "start_timestamp": time(),
        "last_query_timestamp": time(),
        "verification_code": verification_code,
        "parsed_actions": [],
        "current_action_in_progress": None,
    }
    SESSIONS[session_id].update(config.convert_to_dict())
    SESSIONS[session_id]["active_plugins"] = str([plugin.get_plugin_name() for plugin in ACTIVE_PLUGINS])
    SESSIONS[session_id]["researcher_notes"] = ""

    result["status"] = SUCCESS

    session = SESSIONS[session_id]
    model_name = result["engine"].strip()
    domain = result["domain"] if "domain" in result else ""

    # pylint: disable=possibly-used-before-assignment
    append_session_to_file(session, metadata_path)
    print_verbose("New session created", session, verbose)
    # pylint: disable=possibly-used-before-assignment

    print_current_sessions(
        SESSIONS,
        f"Session {session_id} ({domain}: {model_name}) has been started successfully.",
    )

    gc.collect(generation=2)
    return jsonify(result)


@app.route("/api/end_session", methods=["POST"])
@cross_origin(origin="*")
def end_session():
    content = request.json
    session_id = content["sessionId"]
    log = content["logs"]
    remove_session = content.get("remove_session", True)  # Default to True for backward compatibility

    # pylint: disable=possibly-used-before-assignment
    path = os.path.join(proj_dir, session_id) + ".jsonl"
    # pylint: enable=possibly-used-before-assignment

    results = {}
    results["path"] = path
    try:
        save_log_to_jsonl(path, log)
        results["status"] = SUCCESS
    except Exception as e:
        results["status"] = FAILURE
        results["message"] = str(e)
        print(e)
    print_verbose(
        "Save log to file",
        {
            "session_id": session_id,
            "len(log)": len(log),
            "status": results["status"],
        },
        verbose,
    )

    # Remove a finished session only if remove_session is True
    try:
        session = SESSIONS[session_id]
        results["verification_code"] = session["verification_code"]
        if remove_session:
            SESSIONS.pop(session_id)
            print_current_sessions(
                SESSIONS,
                f"Session {session_id} has been saved and removed successfully.",
            )
        else:
            print_current_sessions(
                SESSIONS,
                f"Session {session_id} has been saved successfully (session kept active).",
            )
    except Exception as e:
        print(e)
        print("# Error at the end of end_session; ignore")
        results["verification_code"] = "SERVER_ERROR"
        print_current_sessions(SESSIONS, f"Session {session_id} has not been saved.")

    gc.collect(generation=2)
    return jsonify(results)


@app.route("/api/query", methods=["POST"])
@cross_origin(origin="*")
def query():
    # Step 1
    content = request.json
    session_id = content["session_id"]
    logs = content["logs"]

    prev_suggestions = content["suggestions"]

    results = {}
    try:
        SESSIONS[session_id]["last_query_timestamp"] = time()
    except Exception as e:
        print(f"# Ignoring an error in query: {e}")

    # Check if session ID is valid
    if session_id not in SESSIONS:
        results["status"] = FAILURE
        results["message"] = (
            "Your session has not been established due to invalid access code. Please check your access code in URL."
        )
        return jsonify(results)

    example = content["example"]
    example_text = examples[example]  # pylint: disable=possibly-used-before-assignment

    # Overwrite example text if it is manually provided
    if "example_text" in content:
        example_text = content["example_text"]

    # Get configurations
    n = int(content["n"])
    max_tokens = int(content["max_tokens"])
    temperature = float(content["temperature"])
    top_p = float(content["top_p"])
    presence_penalty = float(content["presence_penalty"])
    frequency_penalty = float(content["frequency_penalty"])

    engine = content["engine"] if "engine" in content else None
    context_window_size = get_context_window_size(engine)

    stop = [sequence for sequence in content["stop"] if len(sequence) > 0]
    if "DO_NOT_STOP" in stop:
        stop = []

    # Remove special characters
    stop_sequence = [sequence for sequence in stop if sequence not in {"."}]
    stop_rules = [sequence for sequence in stop if sequence in {"."}]
    if not stop_sequence:
        stop_sequence = None

    # Step 2
    detected_plugins = analyze_and_update_actions(session_id, logs)

    # Parse doc
    doc = content["doc"]

    modify_prompt = SESSIONS[session_id]["show_interventions"] and True in [
        plugin.intervention_action().intervention_type == InterventionEnum.MODIFY_QUERY
        for plugin in detected_plugins
    ]

    if modify_prompt:
        results = parse_modified_prompt(doc, max_tokens, context_window_size)
    else:
        results = parse_prompt(example_text + doc, max_tokens, context_window_size)

    prompt = results["effective_prompt"]

    # Query GPT-3
    openai_start_time = time()
    try:
        if DEV_MODE:
            # DEV_MODE: return no suggestions
            suggestions = []
            openai_end_time = time()
        else:
            client = OpenAI(api_key=api_keys[("openai", "default")])  # pylint: disable=possibly-used-before-assignment
            if "---" in prompt:  # If the demarcation is there, then suggest an insertion
                prompt, suffix = prompt.split("---")
                response = client.completions.create(  # NOTE: originally was openai.Completion.create, but that was deprecated
                    model=engine,
                    prompt=prompt,
                    suffix=suffix,
                    n=n,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    logprobs=10,
                    stop=stop_sequence,
                )
            else:
                response = client.completions.create(  # NOTE: originally was openai.Completion.create, but that was deprecated
                    model=engine,
                    prompt=prompt,
                    n=n,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    logprobs=10,
                    stop=stop_sequence,
                )
            openai_end_time = time()
            suggestions = []
            for choice in response.choices:
                suggestion = parse_suggestion(choice.text, results["after_prompt"], stop_rules)
                probability = parse_probability(choice.logprobs)
                suggestions.append((suggestion, probability, engine))
    except Exception as e:
        openai_end_time = time()
        results["status"] = FAILURE
        results["message"] = str(e)
        print(e)
        results["openai_time"] = openai_end_time - openai_start_time
        return jsonify(results)

    # Always return original model outputs
    original_suggestions = []
    for index, (suggestion, probability, source) in enumerate(suggestions):
        original_suggestions.append(
            {
                "original": suggestion,
                "trimmed": suggestion.strip(),
                "probability": probability,
                "source": source,
            }
        )

    # Filter out model outputs for safety
    # pylint: disable=possibly-used-before-assignment
    filtered_suggestions, counts = filter_suggestions(
        suggestions,
        prev_suggestions,
        blocklist,
    )
    # pylint: enable=possibly-used-before-assignment
    random.shuffle(filtered_suggestions)

    suggestions_with_probabilities = []
    for index, (suggestion, probability, source) in enumerate(filtered_suggestions):
        suggestions_with_probabilities.append(
            {
                "index": index,
                "original": suggestion,
                "trimmed": suggestion.strip(),
                "probability": probability,
                "source": source,
            }
        )

    results["status"] = SUCCESS
    results["original_suggestions"] = original_suggestions
    results["suggestions_with_probabilities"] = suggestions_with_probabilities
    results["ctrl"] = {
        "n": n,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "stop": stop,
    }
    results["counts"] = counts
    results["openai_time"] = openai_end_time - openai_start_time
    print_verbose("Result", results, verbose)
    return jsonify(results)


@app.route("/api/get_log", methods=["POST"])
@cross_origin(origin="*")
def get_log():
    results = dict()

    content = request.json
    session_id = content["sessionId"]

    # Retrieve the latest list of logs
    log_paths = retrieve_log_paths(args.replay_dir)  # pylint: disable=possibly-used-before-assignment

    try:
        log_path = log_paths[session_id]
        log = read_log(log_path)
        results["status"] = SUCCESS
        results["logs"] = log
    except Exception as e:
        results["status"] = FAILURE
        results["message"] = str(e)

    if results["status"] == FAILURE:
        return results

    # Populate metadata
    try:
        stats = compute_stats(log)
        last_text = get_last_text_from_log(log)
        config = get_config_for_log(session_id, metadata, metadata_path)  # pylint: disable=possibly-used-before-assignment
    except Exception as e:
        print(f"# Failed to retrieve metadata for the log: {e}")
        stats = None
        last_text = None
        config = None
    results["stats"] = stats
    results["config"] = config
    results["last_text"] = last_text

    print_verbose("Get log", results, verbose)
    return results


@app.route("/api/parse_logs", methods=["POST"])
@cross_origin(origin="*")
def parse_logs():
    """New route for handling log parsing. It
    1. Obtains raw logs from the fronted
    2. Invokes ActionsParserAnalyzer to parse new
    current_action_in_progress and the list of parsed actions
    3. Updates parsed_actions global variable
    4. Goes through the list of new actions and if switches the
    intervention_on variable if topic shift is detected
    """
    # Step 1
    content = request.json
    session_id = content["session_id"]
    logs = content["logs"]

    try:
        # Step 2
        detected_plugins = analyze_and_update_actions(session_id, logs)

        if SESSIONS[session_id]["show_interventions"] and len(detected_plugins) > 0:
            return jsonify(
                {
                    "status": SUCCESS,
                    "alert_author": True,
                    "intervention_type": detected_plugins[0].intervention_action().intervention_type,
                    "message": detected_plugins[0].intervention_action().intervention_message,
                }
            )
        else:
            return jsonify({"status": SUCCESS, "alert_author": False})
    except Exception as e:
        print(f"# Parsing failed: {e}")
        return jsonify({"status": FAILURE, "alert_author": False})


def analyze_and_update_actions(session_id, logs):
    """
    Helper function to analyze actions and update session state.
    Returns (new_actions, detected_plugins).
    """
    actions_analyzer = SameSentenceMergeAnalyzer(
        last_action=SESSIONS[session_id]["current_action_in_progress"],
        raw_logs=logs,
    )

    SESSIONS[session_id]["current_action_in_progress"] = actions_analyzer.last_action
    new_actions = actions_analyzer.actions_lst
    for action in new_actions:
        action["level_1_action_type"] = action["action_type"]

    if actions_analyzer.last_action is not None:
        actions_analyzer.last_action = convert_last_action_to_complete_action(actions_analyzer.last_action)

    new_actions = parse_level_3_actions(
        {"current_session": new_actions}, similarity_fcn=get_spacy_similarity
    )["current_session"]

    if len(new_actions) > 0:
        SESSIONS[session_id]["parsed_actions"] += new_actions[:-1]  # update the parsed actions parameter

    detected_plugins = check_for_level_3_actions(
        new_actions, ACTIVE_PLUGINS, n_actions=1, pattern_count_threshold=1
    )
    return detected_plugins


if __name__ == "__main__":
    parser = ArgumentParser()

    # Required arguments
    parser.add_argument("--config_dir", type=str, required=True)
    parser.add_argument("--log_dir", type=str, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--proj_name", type=str, required=True)

    # Optional arguments
    parser.add_argument("--replay_dir", type=str, default="../logs")

    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    parser.add_argument("--use_blocklist", action="store_true")

    global args
    args = parser.parse_args()

    # Create a project directory to store logs
    global config_dir, proj_dir
    config_dir = args.config_dir
    proj_dir = os.path.join(args.log_dir, args.proj_name)
    if not os.path.exists(args.log_dir):
        os.mkdir(args.log_dir)
    if not os.path.exists(proj_dir):
        os.mkdir(proj_dir)

    # Create a text file for storing metadata
    global metadata_path
    metadata_path = os.path.join(args.log_dir, "metadata.txt")
    if not os.path.exists(metadata_path):
        with open(metadata_path, "w") as f:
            f.write("")

    # Read and set API keys
    global api_keys
    api_keys = read_api_keys(config_dir)
    if not DEV_MODE:
        openai.api_key = api_keys[("openai", "default")]

    # Read examples (hidden prompts), prompts, and a blocklist
    global examples, prompts, blocklist
    examples = read_examples(config_dir)
    prompts = read_prompts(config_dir)
    blocklist = []
    if args.use_blocklist:
        blocklist = read_blocklist(config_dir)
        print(f" # Using a blocklist: {len(blocklist)}")

    # Read access codes
    global allowed_access_codes
    allowed_access_codes = read_access_codes(config_dir)

    global session_id_history
    metadata = dict()
    metadata = update_metadata(metadata, metadata_path)

    global verbose
    verbose = args.verbose

    app.run(
        host="0.0.0.0",
        port=args.port,
        debug=args.debug,
    )
