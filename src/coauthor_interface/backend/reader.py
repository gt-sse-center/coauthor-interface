import csv
import json
from pathlib import Path

from coauthor_interface.backend.access_code import AccessCodeConfig


def read_api_keys(config_dir):
    """Read API keys from a CSV file."""
    path = Path(config_dir) / "api_keys.csv"

    api_keys = dict()
    if not path.exists():
        raise RuntimeError(f"Cannot find API keys in the file: {path}")

    with open(path) as f:
        rows = csv.DictReader(f)
        for row in rows:
            host = row["host"]  # 'openai', 'ai21labs', 'anthropic', 'eleutherai', etc.
            domain = row["domain"]  # 'default', 'story', 'essay', etc.

            api_keys[(host, domain)] = row["key"]
    return api_keys


def read_log(log_path):
    """Read a log file."""
    log = []
    path = Path(log_path)

    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    if path.suffix == ".json":
        with open(path) as f:
            log = json.load(f)
    elif path.suffix == ".jsonl":
        with open(path) as f:
            for line in f:
                log.append(json.loads(line))
    else:
        print("# Unknown file extension:", log_path)
    return log


def read_examples(config_dir):
    """Read all examples from config_dir."""
    path = Path(config_dir) / "examples"
    examples = {"na": ""}

    if not path.exists():
        print(f"# Path does not exist: {path}")
        return examples

    paths = []
    for file_path in path.iterdir():
        if file_path.suffix == ".txt":
            paths.append(file_path)

    for file_path in paths:
        name = file_path.stem
        with open(file_path) as f:
            text = f.read().replace("\\n", "\n")
            text = text + " "
        examples[name] = text
    return examples


def read_prompts(config_dir):
    """Read all prompts from config_dir."""
    path = Path(config_dir) / "prompts.tsv"

    if not path.exists():
        raise FileNotFoundError(f"Prompts file not found: {path}")

    prompts = {"na": ""}
    with open(path) as f:
        rows = csv.reader(f, delimiter="\t", quotechar='"')
        for row in rows:
            if len(row) != 3:
                continue

            prompt_code = row[1]
            prompt = row[2].replace("\\n", "\n")
            prompts[prompt_code] = prompt
    return prompts


def read_access_codes(config_dir):
    """Read all access codes from config_dir.

    Return a dictionary with access codes as keys and configs as values.
    """
    access_codes = dict()
    config_path = Path(config_dir)

    # Retrieve all file names that contain 'access_code'
    if not config_path.exists():
        raise RuntimeError(f"Cannot find access code at {config_dir}")

    paths = []
    for file_path in config_path.iterdir():
        if "access_code" in file_path.name and file_path.suffix == ".csv":
            paths.append(file_path)

    # Read access codes with configs
    for file_path in paths:
        with open(file_path) as f:
            input_file = csv.DictReader(f)

            for row in input_file:
                if "access_code" not in row:
                    print(f"# Could not find access_code in {file_path}:\n{row}")
                    continue

                access_code = row["access_code"]
                config = AccessCodeConfig(row)
                access_codes[access_code] = config
    return access_codes


def update_metadata(metadata, metadata_path):
    """Update metadata with the most recent history."""
    path = Path(metadata_path)

    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    with open(path) as f:
        lines = f.read().split("\n")
        for line in lines:
            if not line:  # Skip empty line at the end
                continue
            history = json.loads(line)
            session_id = history["session_id"]

            # Overwrite with the most recent history
            metadata[session_id] = history
    return metadata


def read_blocklist(config_dir):
    """Read blocklist from a text file."""
    path = Path(config_dir) / "blocklist.txt"

    if not path.exists():
        raise FileNotFoundError(f"Blocklist file not found: {path}")

    blocklist = set()
    with open(path) as f:
        lines = f.read().split("\n")
        for line in lines:
            if not line:  # Skip empty line at the end
                continue
            blocklist.add(line.strip())
    return blocklist
