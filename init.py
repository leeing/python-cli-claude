#!/usr/bin/env python3
"""python-cli-claude init — Scaffold a Python CLI project with Claude Code rules.

Usage:
  python init.py <target-dir> [--dry-run] [--no-hooks] [--help] [--version]

One command scaffolding for the python-cli Claude Code template.
"""

from __future__ import annotations

import json
import shutil
import sys
from contextlib import suppress
from pathlib import Path
from typing import TextIO

# ── ANSI helpers ──────────────────────────────────────────────────────────────
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

VERSION = "0.1.0"


# ── Argument parsing ──────────────────────────────────────────────────────────

class CliError(ValueError):
    """Raised when CLI input is invalid."""

    def __init__(self, message: str, *, show_usage: bool = False, is_error: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.show_usage = show_usage
        self.is_error = is_error


def parse_args(argv: list[str]) -> tuple[Path, bool, bool]:
    """Parse CLI arguments. Returns (target_dir, dry_run, no_hooks)."""
    positional: list[str] = []
    dry_run = False
    no_hooks = False
    index = 0

    while index < len(argv):
        arg = argv[index]
        if arg in {"-h", "--help"}:
            help_message = ""
            raise CliError(help_message, show_usage=True, is_error=False)
        if arg in {"-V", "--version"}:
            raise CliError(VERSION, is_error=False)
        if arg == "--dry-run":
            dry_run = True
            index += 1
            continue
        if arg == "--no-hooks":
            no_hooks = True
            index += 1
            continue
        if arg.startswith("-"):
            msg = f"未知参数: {arg}"
            raise CliError(msg, show_usage=True)
        positional.append(arg)
        index += 1

    if len(positional) < 1:
        missing_msg = "缺少参数"
        raise CliError(missing_msg)

    return Path(positional[0]).absolute(), dry_run, no_hooks


# ── Console output ────────────────────────────────────────────────────────────

class Console:
    """Minimal ANSI-aware terminal output."""

    def __init__(self, stdin: TextIO, stdout: TextIO, stderr: TextIO) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def write(self, message: str = "") -> None:
        self.stdout.write(f"{message}\n")
        self.stdout.flush()

    def info(self, message: str) -> None:
        self.stdout.write(f"{GREEN}✓{NC} {message}\n")
        self.stdout.flush()

    def warn(self, message: str) -> None:
        self.stdout.write(f"{YELLOW}⚠{NC} {message}\n")
        self.stdout.flush()

    def error(self, message: str) -> None:
        self.stderr.write(f"{RED}✗{NC} {message}\n")
        self.stderr.flush()

    def prompt_overwrite(self, path: Path, label: str) -> bool:
        """Ask whether an existing path should be overwritten."""
        if not path.exists():
            return True
        self.stdout.write(f"{YELLOW}⚠{NC} {label} 已存在，是否覆盖？[y/N] ")
        self.stdout.flush()
        answer = self.stdin.readline().strip()
        if answer not in {"y", "Y"}:
            self.warn(f"跳过 {label}")
            return False
        return True


# ── File operations ───────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent / "project"


def _try_make_executable(path: Path) -> None:
    """Make a file executable (no-op on platforms that don't support it)."""
    with suppress(NotImplementedError, OSError):
        path.chmod(0o755)


def copy_file(source: Path, target: Path, console: Console, label: str) -> bool:
    """Copy a single file. Returns True if written."""
    if not console.prompt_overwrite(target, label):
        return False
    shutil.copyfile(source, target)
    return True


def copy_skills(target_dir: Path, console: Console, *, dry_run: bool) -> bool:
    """Copy skills from project/.claude/skills/ to target. Returns True if written."""
    source_dir = PROJECT_DIR / ".claude" / "skills"
    target_skills = target_dir / ".claude" / "skills"
    label = ".claude/skills/"

    if dry_run:
        console.info(f"[dry-run] 将生成 {label}")
        return True

    if not console.prompt_overwrite(target_skills, label):
        return False

    if target_skills.exists():
        shutil.rmtree(target_skills)
    target_skills.mkdir(parents=True, exist_ok=True)

    for skill_dir in sorted(source_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        shutil.copytree(skill_dir, target_skills / skill_dir.name)

    return True


def merge_settings(target_settings: Path, source_settings: Path) -> None:
    """Merge hook settings — preserve non-hook keys, dedupe matchers."""
    new_settings = json.loads(source_settings.read_text(encoding="utf-8"))
    existing = json.loads(target_settings.read_text(encoding="utf-8")) if target_settings.exists() else {}

    new_hooks = new_settings.get("hooks", {})
    existing_hooks = existing.get("hooks", {})

    for event_name, new_matchers in new_hooks.items():
        if event_name not in existing_hooks:
            existing_hooks[event_name] = []
        existing_patterns = {m.get("matcher") for m in existing_hooks[event_name]}
        for matcher in new_matchers:
            if matcher.get("matcher") not in existing_patterns:
                existing_hooks[event_name].append(matcher)

    existing["hooks"] = existing_hooks
    target_settings.parent.mkdir(parents=True, exist_ok=True)
    target_settings.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_hooks(target_dir: Path, console: Console, *, dry_run: bool) -> bool:
    """Copy hooks from project/.claude/hooks/ and merge settings.json. Returns True if written."""
    source_dir = PROJECT_DIR / ".claude" / "hooks"
    target_hooks = target_dir / ".claude" / "hooks"
    label = ".claude/hooks/ (hooks)"

    if dry_run:
        console.info(f"[dry-run] 将生成 {label}")
        return True

    if not console.prompt_overwrite(target_hooks, label):
        return False

    target_hooks.mkdir(parents=True, exist_ok=True)
    for hook_file in sorted(source_dir.glob("*.py")):
        dest = target_hooks / hook_file.name
        shutil.copyfile(hook_file, dest)
        _try_make_executable(dest)

    # Merge settings.json
    source_settings = PROJECT_DIR / ".claude" / "settings.json"
    target_settings = target_dir / ".claude" / "settings.json"
    merge_settings(target_settings, source_settings)

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def usage() -> str:
    return f"""\
{BOLD}用法:{NC} python init.py <target-dir> [--dry-run] [--no-hooks]

{BOLD}选项:{NC}
  --dry-run   仅预览将生成的文件，不实际写入
  --no-hooks  跳过 .claude/hooks/ 安装
  --help      显示此帮助信息
  --version   显示版本号

{BOLD}示例:{NC}
  python init.py ~/my-cli-app
  python init.py ~/my-cli-app --dry-run
  python init.py ~/my-cli-app --no-hooks\
"""


def run(argv: list[str], stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    console = Console(stdin=stdin, stdout=stdout, stderr=stderr)

    try:
        target_dir, dry_run, no_hooks = parse_args(argv)
    except CliError as exc:
        if exc.message:
            if exc.is_error:
                console.error(exc.message)
            else:
                console.write(exc.message)
        if exc.show_usage:
            console.write()
            console.write(usage())
        return 1 if exc.is_error else 0

    # Header
    console.write()
    console.write(f"{BOLD}python-cli-claude init{NC}")
    console.write(f"目标: {GREEN}{target_dir}{NC}")
    if dry_run:
        console.write(f"模式: {CYAN}dry-run (预览){NC}")
    if no_hooks:
        console.write(f"安装: {CYAN}跳过 hooks{NC}")
    console.write()

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    # 1. CLAUDE.md
    claude_source = PROJECT_DIR / "CLAUDE.md"
    claude_dest = target_dir / "CLAUDE.md"
    claude_written = False
    if dry_run:
        console.info(f"[dry-run] 将生成 CLAUDE.md → {claude_dest}")
        claude_written = True
    else:
        claude_written = copy_file(claude_source, claude_dest, console, "CLAUDE.md")
        if claude_written:
            console.info(f"CLAUDE.md → {claude_dest}")

    # 2. Skills
    skills_written = copy_skills(target_dir, console, dry_run=dry_run)
    if skills_written and not dry_run:
        console.info(f".claude/skills/ → {target_dir / '.claude/skills/'}")

    # 3. Hooks (unless --no-hooks)
    hooks_written = False
    if not no_hooks:
        hooks_written = copy_hooks(target_dir, console, dry_run=dry_run)
        if hooks_written and not dry_run:
            console.info(f".claude/hooks/ → {target_dir / '.claude/hooks/'}")

    # Summary
    console.write()
    console.write(f"{GREEN}{BOLD}✓ 初始化完成！{NC}")
    console.write()
    console.write(f"{BOLD}已生成:{NC}")

    def summary_item(label: str, *, written: bool) -> None:
        if written:
            console.write(f"  📄 {label}")
        else:
            console.write(f"  📄 {label} {YELLOW}(已跳过){NC}")

    summary_item("CLAUDE.md", written=claude_written)
    summary_item(".claude/skills/ (5 个 skill)", written=skills_written)
    if not no_hooks:
        summary_item(".claude/hooks/ (4 个 hook + settings.json)", written=hooks_written)

    console.write()
    console.write(f"{BOLD}下一步:{NC}")
    console.write("  1. cd 进入项目目录，根据实际情况定制 CLAUDE.md §6 项目特有陷阱")
    console.write("  2. 将 global/CLAUDE.md 设为全局自定义指令（如未设置）")
    console.write()

    return 0


def main() -> int:
    return run(sys.argv[1:], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
