#!/usr/bin/env python3
"""Shared helpers for claude-rules project hook scripts."""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

HOOK_TOOL_DIRS = {".claude", ".codex", ".opencode"}
AUTO_GATE_STATE_DIR = ".auto-gate-state"
AUTO_GATE_PENDING_FILE = "pending"


def find_project_root() -> Path:
    """Resolve the project root from hook environment, install path, or cwd."""
    env_root = (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("OPENCODE_PROJECT_DIR")
    )
    if env_root:
        return Path(env_root).resolve()

    script_path = Path(__file__).resolve()
    if script_path.parent.name == "hooks" and script_path.parent.parent.name in HOOK_TOOL_DIRS:
        return script_path.parent.parent.parent
    return Path.cwd().resolve()


def current_tool_dir() -> str:
    """Return the installed tool directory name, defaulting to .claude."""
    script_path = Path(__file__).resolve()
    if script_path.parent.name == "hooks" and script_path.parent.parent.name in HOOK_TOOL_DIRS:
        return script_path.parent.parent.name
    return ".claude"


def hook_log(event: str, hook_name: str, detail: str = "") -> None:
    """Append a hook log line under the active tool directory."""
    log_dir = find_project_root() / current_tool_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    with contextlib.suppress(OSError):
        (log_dir / "hooks.log").open("a", encoding="utf-8").write(
            f"{timestamp} | {event:<12} | {hook_name:<25} | {detail}\n"
        )


def is_installed_hook_file(path: Path) -> bool:
    """Return True when a file path is inside a generated hook directory."""
    return "hooks" in path.parts and any(tool_dir in path.parts for tool_dir in HOOK_TOOL_DIRS)


def _auto_gate_marker(project_root: Path | None = None) -> Path:
    root = find_project_root() if project_root is None else project_root
    return root / current_tool_dir() / "hooks" / AUTO_GATE_STATE_DIR / AUTO_GATE_PENDING_FILE


def mark_auto_gate_activity(project_root: Path | None = None) -> None:
    """Record that a write-like tool ran and Stop auto-gate should check the project."""
    marker = _auto_gate_marker(project_root)
    with contextlib.suppress(OSError):
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("1\n", encoding="utf-8")


def consume_auto_gate_activity(project_root: Path | None = None) -> bool:
    """Return and clear whether a write-like tool ran since the previous Stop hook."""
    marker = _auto_gate_marker(project_root)
    if not marker.is_file():
        return False
    with contextlib.suppress(OSError):
        marker.unlink()
    return True


def changed_py_files() -> list[str]:
    """Return list of .py files changed relative to HEAD (staged + unstaged + untracked)."""
    try:
        tracked = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=False,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=False,
        )
        all_files = (tracked.stdout.strip() + "\n" + untracked.stdout.strip()).strip().splitlines()
        return [f for f in all_files if f.endswith(".py") and Path(f).exists()]
    except FileNotFoundError:
        return []


def run_capture(label: str, args: list[str]) -> tuple[str, bool, str]:
    """Run a command, return (label, success, output)."""
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    return label, result.returncode == 0, output


# ---------------------------------------------------------------------------
# Shared constraint checks reused across template check-constraints.py hooks
# ---------------------------------------------------------------------------


def _is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") or path.name == "conftest.py" or "tests" in path.parts


def check_bare_exception(file_path: Path) -> list[str]:
    """Detect bare `except Exception` / `except BaseException` / `except:` in non-test .py files."""
    if _is_test_file(file_path):
        return []
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"except\s+(Exception|BaseException)\b", line) or re.search(r"except\s*:", line):
            hits.append(f"  {i}:{line.strip()[:120]}")
    if hits:
        return [
            "❌ Generic except clause detected. Catch specific exception types instead:\n" + "\n".join(hits)
        ]
    return []


def check_legacy_type_hints(file_path: Path) -> list[str]:
    """Detect legacy type hints (Optional, Union, List, Dict) in non-test .py files."""
    if _is_test_file(file_path):
        return []
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"\b(Optional|Union|List|Dict)\[", line):
            hits.append(f"  {i}:{line.strip()[:120]}")
    if hits:
        return [
            "❌ Legacy type hints (Optional/Union/List/Dict) detected. "
            "Use modern syntax (X | None, list[X], dict[K, V]):\n" + "\n".join(hits)
        ]
    return []


def check_assert_usage(file_path: Path) -> list[str]:
    """Detect `assert` statements in non-test .py files (business validation must use explicit raises)."""
    if _is_test_file(file_path):
        return []
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"^\s*assert\s", line):
            hits.append(f"  {i}:{line.strip()[:120]}")
    if hits:
        return [
            "❌ assert statement in non-test code. "
            "Use explicit validation (raise ValueError etc.) instead:\n" + "\n".join(hits)
        ]
    return []


def check_sql_concatenation(file_path: Path) -> list[str]:
    """Detect f-string / string concatenation in SQL queries in non-test .py files."""
    if _is_test_file(file_path):
        return []
    sql_keywords = r"SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER"
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        stripped = line.strip()[:120]
        if re.search(rf'f["\'].*({sql_keywords})\b', line, re.IGNORECASE) or re.search(
            rf'["\'].*({sql_keywords})\b.*["\']\s*\+', line, re.IGNORECASE
        ):
            hits.append(f"  {i}:{stripped}")
    if hits:
        return [
            "❌ SQL string concatenation / f-string detected. "
            "Use parameterized queries or ORM methods:\n" + "\n".join(hits)
        ]
    return []


def check_time_sleep(file_path: Path) -> list[str]:
    """time.sleep() blocks the event loop — use asyncio.sleep() in async contexts."""
    if _is_test_file(file_path):
        return []
    hits: list[str] = []
    for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"\btime\.sleep\s*\(", line):
            hits.append(f"  {i}:{line.strip()[:120]}")
    if hits:
        return [
            "❌ time.sleep() detected. Use asyncio.sleep() in async contexts "
            "or replace polling with event-driven logic:\n" + "\n".join(hits)
        ]
    return []


def check_requests_usage(file_path: Path) -> list[str]:
    """requests is a sync HTTP library — use httpx with async instead."""
    if _is_test_file(file_path):
        return []
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"^\s*(?:import requests|from requests\b)", text, re.MULTILINE):
        return [
            "❌ requests library detected. Use httpx with async/await instead:\n"
            "  - Replace: import requests\n"
            "  - With:    import httpx  (use async with httpx.AsyncClient() as client:)"
        ]
    return []
