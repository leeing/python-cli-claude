"""Tests for the python-cli-claude init CLI."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_INIT = REPO_ROOT / "init.py"


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from command output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def read_tree(root: Path) -> dict[str, str]:
    """Read all generated files under a directory."""
    contents: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        contents[str(p.relative_to(root))] = p.read_text(encoding="utf-8")
    return contents


def make_target_dir(tmp: Path) -> Path:
    """Return a non-existent target directory inside the given temp directory."""
    return tmp / "target"


class TestInitCli:
    """Tests for the simplified init.py CLI."""

    def test_help_output(self) -> None:
        """--help should succeed and include usage."""
        result = subprocess.run(
            [sys.executable, str(PYTHON_INIT), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "用法:" in strip_ansi(result.stdout)
        assert "--dry-run" in strip_ansi(result.stdout)
        assert "--no-hooks" in strip_ansi(result.stdout)

    def test_missing_args_error(self) -> None:
        """Running without arguments should fail."""
        result = subprocess.run(
            [sys.executable, str(PYTHON_INIT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "缺少参数" in strip_ansi(result.stderr)

    def test_version_output(self) -> None:
        """--version should succeed and print a version string."""
        result = subprocess.run(
            [sys.executable, str(PYTHON_INIT), "--version"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        output = strip_ansi(result.stdout).strip()
        assert output
        assert "0.1.0" in output

    def test_unknown_parameter_error(self) -> None:
        """Unknown flags should fail with a clear message."""
        result = subprocess.run(
            [sys.executable, str(PYTHON_INIT), "/tmp/target", "--bad-flag"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "未知参数" in strip_ansi(result.stderr)

    def test_scaffolds_python_cli_project(self) -> None:
        """Basic init should copy CLAUDE.md, skills, hooks, and settings.json."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = make_target_dir(Path(tmp_dir))
            result = subprocess.run(
                [sys.executable, str(PYTHON_INIT), str(target)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0
            output = strip_ansi(result.stdout)
            assert "初始化完成" in output

            files = read_tree(target)
            # Core file
            assert "CLAUDE.md" in files
            assert "工具链" in files["CLAUDE.md"]

            # Skills
            assert ".claude/skills/acceptance/SKILL.md" in files
            assert ".claude/skills/code-style/SKILL.md" in files
            assert ".claude/skills/debugging/SKILL.md" in files
            assert ".claude/skills/hooks-setup/SKILL.md" in files
            assert ".claude/skills/new-feature/SKILL.md" in files

            # Hooks
            assert ".claude/hooks/_hook_utils.py" in files
            assert ".claude/hooks/auto-gate.py" in files
            assert ".claude/hooks/check-constraints.py" in files
            assert ".claude/hooks/check-scaffold.py" in files

            # Settings
            settings_text = files[".claude/settings.json"]
            assert '"hooks"' in settings_text
            assert '"PostToolUse"' in settings_text
            assert '"Stop"' in settings_text

    def test_dry_run_does_not_create_files(self) -> None:
        """--dry-run should print preview without creating files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = make_target_dir(Path(tmp_dir))
            result = subprocess.run(
                [sys.executable, str(PYTHON_INIT), str(target), "--dry-run"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0
            output = strip_ansi(result.stdout)
            assert "[dry-run]" in output
            assert "初始化完成" in output
            # Target directory should NOT be created
            assert not target.exists()

    def test_no_hooks_skips_hooks(self) -> None:
        """--no-hooks should install CLAUDE.md and skills but skip hooks."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = make_target_dir(Path(tmp_dir))
            result = subprocess.run(
                [sys.executable, str(PYTHON_INIT), str(target), "--no-hooks"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0
            output = strip_ansi(result.stdout)
            assert "跳过 hooks" in output or "no-hooks" in output.lower()

            files = read_tree(target)
            assert "CLAUDE.md" in files
            assert ".claude/skills/acceptance/SKILL.md" in files
            # Hooks and settings should NOT be present
            assert ".claude/hooks/" not in str(list(files.keys()))
            assert ".claude/settings.json" not in files

    def test_overwrite_prompt_skipped(self) -> None:
        """Existing files should be skipped when overwrite is declined."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = make_target_dir(Path(tmp_dir))
            target.mkdir(parents=True)
            (target / "CLAUDE.md").write_text("keep me", encoding="utf-8")
            (target / ".claude").mkdir(exist_ok=True)
            (target / ".claude" / "skills").mkdir(exist_ok=True)
            (target / ".claude" / "hooks").mkdir(exist_ok=True)
            (target / ".claude" / "settings.json").write_text('{"keep": true}', encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(PYTHON_INIT), str(target)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
                input="n\nn\nn\n",  # Decline all three overwrite prompts
            )
            assert result.returncode == 0
            output = strip_ansi(result.stdout)
            assert "(已跳过)" in output

            # Original files should be untouched
            assert Path(target / "CLAUDE.md").read_text(encoding="utf-8") == "keep me"
            assert Path(target / ".claude" / "settings.json").read_text(encoding="utf-8") == '{"keep": true}'

    def test_short_flags_support(self) -> None:
        """-h and -V should also work."""
        result_h = subprocess.run(
            [sys.executable, str(PYTHON_INIT), "-h"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result_h.returncode == 0
        assert "用法:" in strip_ansi(result_h.stdout)

        result_v = subprocess.run(
            [sys.executable, str(PYTHON_INIT), "-V"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result_v.returncode == 0
        assert strip_ansi(result_v.stdout).strip()
