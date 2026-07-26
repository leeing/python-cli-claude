#!/usr/bin/env python3
"""
Claude Code Hook: Enforce python-cli template constraints (PostToolUse / Write|Edit|MultiEdit)

Checks written .py files for template violations and blocks non-conforming writes.
Exit 2 = block (stderr shown to agent as fix instructions), exit 0 = allow.

Adapted from python-stdlib/hooks/check-constraints.py for src/ layout projects
that allow third-party packages and use pydantic-settings for config.
"""

import json
import re
import sys
from pathlib import Path

from _hook_utils import (
    check_assert_usage,
    check_bare_exception,
    check_legacy_type_hints,
    check_requests_usage,
    check_time_sleep,
    hook_log,
    is_installed_hook_file,
)

MAX_TYPE_IGNORES = 3
MAX_FILE_LINES = 1000

SECURITY_NOQA_CODES = {"S307", "S609", "S301", "S302", "S105", "S106", "S107"}


def _is_test_file(p: Path) -> bool:
    return p.name.startswith("test_") or p.name == "conftest.py" or "tests" in p.parts


def check_type_ignores(file_path: Path) -> list[str]:
    if _is_test_file(file_path):
        return []
    count = sum(
        1 for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines() if "# type: ignore" in line
    )
    if count > MAX_TYPE_IGNORES:
        return [f"❌ type: ignore count = {count} (max {MAX_TYPE_IGNORES}). Refactor to eliminate type ignores."]
    return []


def check_security_noqa(file_path: Path) -> list[str]:
    if _is_test_file(file_path):
        return []
    hits: list[str] = []
    noqa_re = re.compile(r"#\s*noqa:\s*\S*(" + "|".join(SECURITY_NOQA_CODES) + r")")
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if noqa_re.search(line):
            hits.append(f"  {i}:{line}")
    if hits:
        return ["❌ Security-critical rules must not be suppressed with noqa:\n" + "\n".join(hits)]
    return []


def check_ospath(file_path: Path) -> list[str]:
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"\bos\.path\.", line):
            hits.append(f"  {i}:{line}")
    if hits:
        return ["❌ os.path detected. Use pathlib.Path instead:\n" + "\n".join(hits)]
    return []


def check_environ_pattern(file_path: Path) -> list[str]:
    """Env vars must go through pydantic-settings (BaseSettings), not raw os.environ/os.getenv."""
    if _is_test_file(file_path):
        return []
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    environ_lines = [
        f"  {line_number}:{line}"
        for line_number, line in enumerate(text.splitlines(), 1)
        if "os.environ" in line or re.search(r"\bos\.getenv\b", line)
    ]
    if not environ_lines:
        return []
    return [
        "❌ os.environ/os.getenv detected. Use pydantic-settings (BaseSettings) instead:\n" + "\n".join(environ_lines)
    ]


def check_file_size(file_path: Path) -> list[str]:
    count = len(file_path.read_text(encoding="utf-8", errors="ignore").splitlines())
    if count > MAX_FILE_LINES:
        return [f"❌ File has {count} lines (max {MAX_FILE_LINES}). Split into modules."]
    return []


def check_print_usage(file_path: Path) -> list[str]:
    if _is_test_file(file_path):
        return []
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"\bprint\s*\(", line):
            hits.append(f"  {i}:{line}")
    if hits:
        return ["❌ print() detected. Use structlog instead:\n" + "\n".join(hits)]
    return []


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    raw_path = data.get("tool_input", {}).get("file_path", "")
    if not raw_path or not raw_path.endswith(".py"):
        sys.exit(0)

    file_path = Path(raw_path)
    if not file_path.is_file():
        sys.exit(0)

    if is_installed_hook_file(file_path):
        sys.exit(0)

    hook_log("PostToolUse", "check-constraints", f"file={file_path}")

    errors: list[str] = []
    errors += check_type_ignores(file_path)
    errors += check_security_noqa(file_path)
    errors += check_ospath(file_path)
    errors += check_environ_pattern(file_path)
    errors += check_file_size(file_path)
    errors += check_print_usage(file_path)
    errors += check_time_sleep(file_path)
    errors += check_requests_usage(file_path)
    errors += check_bare_exception(file_path)
    errors += check_legacy_type_hints(file_path)
    errors += check_assert_usage(file_path)

    if errors:
        hook_log("PostToolUse", "check-constraints", f"REJECTED:{file_path}")
        for err in errors:
            print(err, file=sys.stderr)
        print(f"\n🚫 Constraint check failed for {file_path}. Fix the issues above.", file=sys.stderr)
        sys.exit(2)

    hook_log("PostToolUse", "check-constraints", f"PASS:{file_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
