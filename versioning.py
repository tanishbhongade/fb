import hashlib
import json
from pathlib import Path
import re
from collections import Counter
import argparse
from datetime import datetime


# ----------------------------
# Paths
# ----------------------------
BASE_DIR = Path("dataset_repo")
RAW_DIR = BASE_DIR / "raw_data"
VERSIONS_DIR = BASE_DIR / "versions"
LOG_FILE = BASE_DIR / "version_log.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Generate SHA-256 Hash
# ----------------------------
def generate_hash(raw_text, config_dict):
    config_string = json.dumps(config_dict, sort_keys=True)
    combined = raw_text + config_string
    return hashlib.sha256(combined.encode()).hexdigest()


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
# Compute Metrics
# ----------------------------
def compute_metrics(text):
    lines = text.splitlines()
    tokens = text.split()

    num_lines = len(lines)
    total_tokens = len(tokens)
    unique_tokens = len(set(tokens))
    avg_tokens_per_line = total_tokens / num_lines if num_lines > 0 else 0

    line_counts = Counter(lines)
    duplicate_lines = sum(count - 1 for count in line_counts.values() if count > 1)

    return {
        "num_lines": num_lines,
        "total_tokens": total_tokens,
        "unique_tokens": unique_tokens,
        "avg_tokens_per_line": avg_tokens_per_line,
        "duplicate_lines": duplicate_lines,
    }


# ----------------------------
# Save Version
# ----------------------------
def create_version(raw_file_path, config_file_path):
    raw_text = Path(raw_file_path).read_text()
    config = json.loads(Path(config_file_path).read_text())

    version_id = generate_hash(raw_text, config)
    version_path = VERSIONS_DIR / version_id

    if version_path.exists():
        print("Version already exists:", version_id)
        return

    version_path.mkdir()

    processed_text = preprocess_text(raw_text, config)
    metrics = compute_metrics(processed_text)

    # Save files
    (version_path / "processed.txt").write_text(processed_text)
    (version_path / "config.json").write_text(json.dumps(config, indent=4))
    (version_path / "metrics.json").write_text(json.dumps(metrics, indent=4))

    log_version(version_id, config)

    print("New version created:", version_id)


# ----------------------------
# Logging
# ----------------------------
def log_version(version_id, config):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {
        "version_id": version_id,
        "timestamp": timestamp,
        "config": config,
    }

    if LOG_FILE.exists():
        logs = json.loads(LOG_FILE.read_text())
    else:
        logs = []

    logs.append(log_entry)
    LOG_FILE.write_text(json.dumps(logs, indent=4))


def show_logs():
    if not LOG_FILE.exists():
        print("No version history found.")
        return

    logs = json.loads(LOG_FILE.read_text())
    for entry in logs:
        print("-" * 40)
        print("Version ID :", entry["version_id"])
        print("Timestamp  :", entry["timestamp"])
        print("Config     :", entry["config"])


# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Minimal Dataset Versioning System")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("raw_file")
    create_parser.add_argument("config_file")

    subparsers.add_parser("log")

    args = parser.parse_args()

    if args.command == "create":
        create_version(args.raw_file, args.config_file)

    elif args.command == "log":
        show_logs()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()