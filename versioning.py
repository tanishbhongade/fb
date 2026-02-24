import hashlib
import json
from pathlib import Path
import re
import argparse
from datetime import datetime

# ----------------------------
# Paths
# ----------------------------
BASE_DIR = Path("dataset_repo")
OBJECTS_DIR = BASE_DIR / "objects"
COMMITS_DIR = BASE_DIR / "commits"
HEAD_FILE = BASE_DIR / "HEAD"

OBJECTS_DIR.mkdir(parents=True, exist_ok=True)
COMMITS_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Hash Utilities
# ----------------------------
def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


# ----------------------------
# Content Addressable Storage
# ----------------------------
def store_object(content: str) -> str:
    object_hash = hash_content(content)

    subdir = OBJECTS_DIR / object_hash[:2]
    subdir.mkdir(parents=True, exist_ok=True)

    object_path = subdir / object_hash[2:]

    # Deduplication happens here
    if not object_path.exists():
        object_path.write_text(content)

    return object_hash


def load_object(object_hash: str) -> str:
    object_path = OBJECTS_DIR / object_hash[:2] / object_hash[2:]
    return object_path.read_text()


# ----------------------------
# Preprocessing
# ----------------------------
def preprocess_text(text, config):
    if config.get("lowercase"):
        text = text.lower()

    if config.get("remove_punctuation"):
        text = re.sub(r"[^\w\s]", "", text)

    lines = text.splitlines()

    if config.get("remove_duplicates"):
        lines = list(dict.fromkeys(lines))

    return "\n".join(lines)


# ----------------------------
# Commit Handling
# ----------------------------
def get_head():
    if HEAD_FILE.exists():
        return HEAD_FILE.read_text().strip()
    return None


def update_head(commit_id):
    HEAD_FILE.write_text(commit_id)


def create_commit(object_hash, config, parent):
    commit_data = {
        "object_hash": object_hash,
        "parent": parent,
        "timestamp": datetime.now().isoformat(),
        "config": config,
    }

    commit_string = json.dumps(commit_data, sort_keys=True)
    commit_id = hash_content(commit_string)

    commit_path = COMMITS_DIR / f"{commit_id}.json"

    if not commit_path.exists():
        commit_path.write_text(json.dumps(commit_data, indent=4))

    return commit_id


def load_commit(commit_id):
    commit_path = COMMITS_DIR / f"{commit_id}.json"
    return json.loads(commit_path.read_text())


# ----------------------------
# Create Version (Commit)
# ----------------------------
def create_version(raw_file_path, config_file_path):
    raw_text = Path(raw_file_path).read_text()
    config = json.loads(Path(config_file_path).read_text())

    processed_text = preprocess_text(raw_text, config)

    object_hash = store_object(processed_text)

    parent = get_head()

    commit_id = create_commit(object_hash, config, parent)

    update_head(commit_id)

    print("New commit created:")
    print(commit_id)


# ----------------------------
# Log History
# ----------------------------
def show_log():
    commit_id = get_head()

    if not commit_id:
        print("No commits yet.")
        return

    while commit_id:
        commit = load_commit(commit_id)

        print("-" * 50)
        print("Commit :", commit_id)
        print("Time   :", commit["timestamp"])
        print("Parent :", commit["parent"])
        print("Config :", commit["config"])

        commit_id = commit["parent"]


# ----------------------------
# Checkout
# ----------------------------
def checkout(commit_id, output_file):
    commit = load_commit(commit_id)
    content = load_object(commit["object_hash"])

    Path(output_file).write_text(content)
    print("Checked out to", output_file)


# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Minimal Dataset Git-Like System")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("raw_file")
    create_parser.add_argument("config_file")

    subparsers.add_parser("log")

    checkout_parser = subparsers.add_parser("checkout")
    checkout_parser.add_argument("commit_id")
    checkout_parser.add_argument("output_file")

    args = parser.parse_args()

    if args.command == "create":
        create_version(args.raw_file, args.config_file)

    elif args.command == "log":
        show_log()

    elif args.command == "checkout":
        checkout(args.commit_id, args.output_file)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
