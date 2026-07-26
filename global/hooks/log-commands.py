#!/usr/bin/env python3
"""
Claude Code Hook: Log All Bash Commands (PostToolUse / Bash)

Appends every bash command to a daily log file for audit trail.
Never blocks — always exits 0.
"""

import json
import os
import sys
from datetime import UTC, datetime

LOG_DIR = os.path.expanduser("~/.claude/hooks-logs")

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    os.makedirs(LOG_DIR, exist_ok=True)

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"commands-{today}.log")

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    cwd = data.get("cwd", os.getcwd())
    session = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    entry = f"[{timestamp}] session={session} cwd={cwd}\n  $ {command}\n"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except OSError:
        pass  # logging failure should never block work

    sys.exit(0)

if __name__ == "__main__":
    main()
