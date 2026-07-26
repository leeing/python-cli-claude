#!/usr/bin/env python3
"""
Claude Code Hook: Protect Critical Files (PreToolUse / Bash|Write|Edit|MultiEdit)

Blocks modification of config files, secrets, and system files.
Exit 2 = block, exit 0 = allow.
"""

import json
import os
import sys

# Exact filenames (matched against basename)
PROTECTED_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "authorized_keys",
    "known_hosts",
}

# Path prefixes to protect (absolute)
PROTECTED_PREFIXES = [
    "/etc/",
    "/usr/",
    "/System/",
    os.path.expanduser("~/.ssh/"),
    os.path.expanduser("~/.gnupg/"),
    os.path.expanduser("~/.claude/settings.json"),  # protect global settings
]

# Path suffixes/patterns
PROTECTED_SUFFIXES = [
    ".pem",
    ".key",
    ".p12",
    ".pfx",
]

def is_protected(file_path: str) -> str | None:
    """Returns reason string if protected, None if allowed."""
    if not file_path:
        return None

    abs_path = os.path.abspath(os.path.expanduser(file_path))
    basename = os.path.basename(abs_path)

    # Check exact basename match
    if basename in PROTECTED_BASENAMES:
        return f"Protected file: {basename} (secrets/keys)"

    # Check path prefixes
    for prefix in PROTECTED_PREFIXES:
        if abs_path.startswith(prefix):
            return f"Protected path: {prefix}"

    # Check suffixes
    for suffix in PROTECTED_SUFFIXES:
        if abs_path.endswith(suffix):
            return f"Protected file type: {suffix} (certificate/key)"

    return None

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    reason = is_protected(file_path)

    if reason:
        print(f"🔒 {reason}", file=sys.stderr)
        print(f"   Path: {file_path}", file=sys.stderr)
        print("   Override: remove from ~/.claude/hooks/protect-files.py", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
