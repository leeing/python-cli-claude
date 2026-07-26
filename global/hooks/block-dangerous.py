#!/usr/bin/env python3
"""
Claude Code Hook: Block Dangerous Commands (PreToolUse / Bash)

Exit codes:
  0 = allow
  2 = block (stderr shown to Claude as reason)
"""

import json
import re
import sys

DANGEROUS_PATTERNS = [
    # Filesystem destruction — rm -rf /, rm -rf ~, rm -rf /*
    (r"rm\s+.*-[a-zA-Z]*r[a-zA-Z]*\s+(/\s*$|/\s|/\*|~/|~\s*$|~\*|\$HOME)",
     "🚫 Blocked: recursive delete on root/home"),
    # dd to raw disk
    (r"dd\s+.*of\s*=\s*/dev/[sh]d", "🚫 Blocked: dd writing to raw disk"),
    # mkfs
    (r"\bmkfs\.", "🚫 Blocked: filesystem format command"),
    # Fork bomb
    (r":\(\)\s*\{.*\|.*&\s*\}", "🚫 Blocked: fork bomb detected"),
    # Pipe to shell (remote code execution)
    (r"(curl|wget)\s+[^|]+\|\s*(ba)?sh", "🚫 Blocked: piping remote content to shell"),
    # Nuclear permissions
    (r"chmod\s+(-R\s+)?777\s+/", "🚫 Blocked: 777 on root"),
    (r"chown\s+-R\s+.*\s+/\s*$", "🚫 Blocked: recursive chown on root"),
    # System shutdown
    (r"\b(shutdown|reboot|halt|poweroff)\s", "🚫 Blocked: system shutdown/reboot"),
    (r"kill\s+-9\s+1\b", "🚫 Blocked: killing init/systemd"),
    # Git force push to main/master
    (r"git\s+push\s+.*--force.*\b(main|master)\b", "🚫 Blocked: force push to main/master"),
    (r"git\s+push\s+-f\s+.*\b(main|master)\b", "🚫 Blocked: force push to main/master"),
    # Any push to main/master (without --force too — must be user-confirmed)
    (r"git\s+push\b[^|&;]*\b(main|master)\b", "🚫 Blocked: push to main/master requires user confirmation"),
    # Merge into main/master
    (r"git\s+merge\b[^|&;]*\b(main|master)\b", "🚫 Blocked: merging into main/master requires user confirmation"),
    # Rebase (any form)
    (r"git\s+rebase\b", "🚫 Blocked: git rebase requires explicit user instruction"),
    # Hard reset losing commits
    (r"git\s+reset\s+--hard\s+HEAD~", "🚫 Blocked: hard reset losing commits"),
    # Truncate system config
    (r">\s*/etc/", "🚫 Blocked: truncating system config"),
    # Python remote exec
    (r"python3?\s+-c\s+.*urllib.*exec", "🚫 Blocked: remote code execution via python"),
]

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

    for pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(message, file=sys.stderr)
            print(f"  Command: {command[:200]}", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
