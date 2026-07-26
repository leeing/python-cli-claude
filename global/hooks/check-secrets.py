#!/usr/bin/env python3
"""
Claude Code Hook: Block Hardcoded Secrets (PreToolUse / Write|Edit|MultiEdit)

Scans file content BEFORE writing to disk, blocking any hardcoded credentials.
Run as PreToolUse so secrets never reach the filesystem.
Exit 2 = block, exit 0 = allow.
"""

import json
import os
import re
import sys

from _path_safety import is_safe_path

# (pattern, human-readable label)
SECRET_PATTERNS: list[tuple[str, str]] = [
    # Generic assignment with suspicious value
    (
        r'(?i)(password|passwd|secret|api_key|apikey|auth_token|access_token)\s*=\s*["\'][^"\']{4,}["\']',
        "Hardcoded credential assignment",
    ),
    # Common provider key prefixes
    (
        r"(?i)\b(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36,}|glpat-[A-Za-z0-9\-]{20,})",
        "API key with known provider prefix",
    ),
    # Private key PEM header in source
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private key embedded in source file"),
    # AWS-style access key
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key ID"),
    # Basic-auth URL with credentials
    (r"https?://[^:@/\s]+:[^:@/\s]{4,}@", "Credentials embedded in URL"),
]

# File types to skip (binary, lock files, etc.)
SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
    ".pyc",
    ".pyo",
}

# Filenames that are intentionally secret-like (test fixtures, examples)
SKIP_BASENAMES = {
    "test_secrets.py",
    "test_global_hooks.py",
    "example.env",
    ".env.example",
    ".env.sample",
}


def should_skip(file_path: str) -> bool:
    _, ext = os.path.splitext(file_path)
    if ext.lower() in SKIP_EXTENSIONS:
        return True
    return os.path.basename(file_path) in SKIP_BASENAMES


def scan_content(content: str) -> list[tuple[int, str, str]]:
    """Returns list of (line_number, matched_text, label) for each hit."""
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(content.splitlines(), 1):
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                safe = line.strip()[:120]
                hits.append((lineno, safe, label))
                break  # one label per line is enough
    return hits


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Security: Prevent path traversal attacks (including symlinks)
    if not is_safe_path(file_path):
        print(f"🚫 Security: Attempted path traversal: {file_path}", file=sys.stderr)
        sys.exit(2)

    if should_skip(file_path):
        sys.exit(0)

    # Scan the content being written (before it hits disk)
    # Write has 'content', Edit has 'new_string', MultiEdit has 'edits[].new_string'
    content_to_scan = ""
    if tool == "Write":
        content_to_scan = tool_input.get("content", "")
    elif tool == "Edit":
        content_to_scan = tool_input.get("new_string", "")
    elif tool == "MultiEdit":
        edits = tool_input.get("edits", [])
        content_to_scan = "\n".join(e.get("new_string", "") for e in edits)

    if not content_to_scan:
        sys.exit(0)

    hits = scan_content(content_to_scan)
    if not hits:
        sys.exit(0)

    print(f"🔑 Potential hardcoded secrets detected (blocked before writing to {file_path}):", file=sys.stderr)
    for lineno, text, label in hits:
        print(f"  Line {lineno}: [{label}]", file=sys.stderr)
        print(f"    {text}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  Fix: use environment variables or a secrets manager instead.", file=sys.stderr)
    print("  If this is a test fixture, add the file to SKIP_BASENAMES in check-secrets.py", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
