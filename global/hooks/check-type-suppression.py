#!/usr/bin/env python3
"""
Claude Code Hook: Block Type-Suppression Accumulation (PostToolUse / Write|Edit|MultiEdit)

Counts type-suppression comments per file. If a single file exceeds MAX_SUPPRESSIONS,
the write is blocked so the agent is forced to refactor instead of accumulating ignores.

Covers:
  Python : # type: ignore
  TypeScript/JavaScript : @ts-ignore, @ts-nocheck, @ts-expect-error
  General : eslint-disable (inline, next-line)

Exit 2 = block, exit 0 = allow.
"""

import json
import os
import re
import sys

from _path_safety import is_safe_path

MAX_SUPPRESSIONS = 3

# Patterns counted as type/lint suppressions
SUPPRESSION_PATTERNS = [
    r"#\s*type:\s*ignore",  # Python mypy
    r"@ts-ignore",  # TypeScript
    r"@ts-nocheck",  # TypeScript (whole-file)
    r"@ts-expect-error",  # TypeScript
    r"eslint-disable(?:-next-line|-line)?\b",  # ESLint inline
]

COMPILED = [re.compile(p) for p in SUPPRESSION_PATTERNS]

SKIP_EXTENSIONS = {".pyc", ".pyo", ".lock", ".png", ".jpg", ".gif", ".woff", ".ttf"}
SKIP_BASENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "test_global_hooks.py",
    "check-type-suppression.py",
}


def count_suppressions(file_path: str) -> list[tuple[int, str]]:
    """Returns list of (line_number, matched_line) for each suppression hit."""
    hits: list[tuple[int, str]] = []
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                for pat in COMPILED:
                    if pat.search(line):
                        hits.append((lineno, line.strip()[:120]))
                        break
    except OSError:
        pass
    return hits


def should_skip(file_path: str) -> bool:
    _, ext = os.path.splitext(file_path)
    if ext.lower() in SKIP_EXTENSIONS:
        return True
    return os.path.basename(file_path) in SKIP_BASENAMES


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Security: Prevent path traversal attacks
    if not is_safe_path(file_path):
        print(f"🚫 Security: Attempted path traversal: {file_path}", file=sys.stderr)
        sys.exit(2)

    if should_skip(file_path):
        sys.exit(0)

    if not os.path.isfile(file_path):
        sys.exit(0)

    hits = count_suppressions(file_path)
    if len(hits) <= MAX_SUPPRESSIONS:
        sys.exit(0)

    print(
        f"🚫 Type-suppression accumulation in {file_path}: {len(hits)} suppressions (max {MAX_SUPPRESSIONS})",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    for lineno, text in hits:
        print(f"  Line {lineno}: {text}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  Fix: refactor to eliminate the suppression comments rather than adding more.", file=sys.stderr)
    print("  Override: raise MAX_SUPPRESSIONS in check-type-suppression.py if justified.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
