#!/usr/bin/env python3
"""
Claude Code Hook: Validate python-cli project scaffold (PostToolUse / Write|Edit|MultiEdit)

Triggered when a .py file is written. Ensures required project files exist.
Exit 2 = block (agent is instructed to create missing files), exit 0 = pass.
"""

import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

PYPROJECT_TEMPLATE = """\
[project]
name = "my-cli"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["ruff", "mypy", "pytest", "structlog"]

[tool.ruff]
target-version = "py312"
line-length = 120
src = ["src"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "B", "UP", "N", "S", "SIM", "T20",
    "PLR", "PLW", "TRY", "G",
    "ARG", "C4", "C90", "EM", "FBT", "DTZ", "PERF", "ISC", "SLOT",
]
unfixable = ["S307", "S609", "S301", "S302", "S105", "S106", "S107"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004", "ARG001"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.mypy]
python_version = "3.12"
strict = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
"""


def hook_log(event: str, hook_name: str, detail: str = "") -> None:
    log_dir_env = (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("OPENCODE_PROJECT_DIR", ".")
    )
    script_parts = Path(__file__).resolve().parts
    tool_dir = ".codex" if ".codex" in script_parts else ".opencode" if ".opencode" in script_parts else ".claude"
    log_dir = Path(log_dir_env) / tool_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    with contextlib.suppress(OSError):
        (log_dir / "hooks.log").open("a").write(f"{ts} | {event:<12} | {hook_name:<25} | {detail}\n")


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

    hook_log("PostToolUse", "check-scaffold", f"file={raw_path}")

    missing: list[str] = []

    if not Path("pyproject.toml").is_file():
        missing.append("pyproject.toml")

    if not Path("src").is_dir():
        missing.append("src/ directory (project uses src layout)")

    test_files = list(Path("tests").rglob("test_*.py")) if Path("tests").is_dir() else []
    if not test_files:
        missing.append("tests/test_*.py (at least one test file required)")

    if not missing:
        hook_log("PostToolUse", "check-scaffold", "PASS")
        sys.exit(0)

    hook_log("PostToolUse", "check-scaffold", "MISSING_FILES")
    print("\n⚠️  Project scaffold incomplete. Missing required files:", file=sys.stderr)
    for f in missing:
        print(f"  - {f}", file=sys.stderr)
    print("\n=== INSTRUCTIONS FOR AI AGENT ===", file=sys.stderr)
    print("DO NOT STOP. Create the missing files listed above.", file=sys.stderr)
    print("", file=sys.stderr)
    print("- pyproject.toml: Copy the template below and adjust [project].name:", file=sys.stderr)
    print(PYPROJECT_TEMPLATE, file=sys.stderr)
    print("=================================", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
