#!/usr/bin/env python3
"""Claude Code Hook: Auto Gate for python-cli template (Stop).

Runs quality checks on **changed files only**, in parallel where possible.
Exit 2 = block task completion (agent must fix and retry), exit 0 = pass.
"""

import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from _hook_utils import changed_py_files, hook_log, run_capture


def main() -> None:
    hook_log("Stop", "auto-gate", "start")

    py_files = changed_py_files()
    if not py_files:
        hook_log("Stop", "auto-gate", "SKIP:no-changes")
        print("✅ Auto Gate: no Python files changed, skipping.")
        sys.exit(0)

    src_files = [f for f in py_files if f.startswith("src/")]
    print(f"--- Auto Gate: checking {len(py_files)} changed file(s) ---", flush=True)

    # Build check tasks to run in parallel
    tasks: dict[str, list[str]] = {
        "ruff-format": ["uv", "run", "ruff", "format", "--check", *py_files],
        "ruff-check": ["uv", "run", "ruff", "check", *py_files],
    }
    if src_files:
        tasks["mypy"] = ["uv", "run", "mypy", *src_files]

    # Run linting tasks in parallel
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures: dict[str, Future[tuple[str, bool, str]]] = {
            label: pool.submit(run_capture, label, args) for label, args in tasks.items()
        }
        for future in futures.values():
            name, ok, output = future.result()
            if ok:
                print(f"✅ {name}", flush=True)
            else:
                failed.append(name)
                print(f"❌ {name}", flush=True)
                print(output, flush=True)
                hook_log("Stop", "auto-gate", f"FAIL:{name}")

    # Run pytest — only test files related to changed modules
    if Path("tests").is_dir():
        test_targets: list[str] = []
        for f in py_files:
            if f.startswith("tests/"):
                test_targets.append(f)
            elif f.startswith("src/"):
                # src/pkg/foo.py → tests/test_foo.py
                stem = Path(f).stem
                candidate = Path("tests") / f"test_{stem}.py"
                if candidate.exists() and str(candidate) not in test_targets:
                    test_targets.append(str(candidate))
        if not test_targets:
            print("✅ pytest (no matching test files, skipped)", flush=True)
        else:
            print(f"--- pytest ({len(test_targets)} file(s)) ---", flush=True)
            try:
                pytest_result = subprocess.run(
                    ["uv", "run", "pytest", *test_targets, "-v", "-x"],
                    text=True,
                    timeout=60,
                    check=False,
                )
                pytest_ok = pytest_result.returncode == 0
            except subprocess.TimeoutExpired:
                pytest_ok = False
                print("⚠️  pytest killed after 60s (likely a hanging test)", flush=True)
            if not pytest_ok:
                failed.append("pytest")
                hook_log("Stop", "auto-gate", "FAIL:pytest")
                print("❌ pytest", file=sys.stderr)

    if failed:
        hook_log("Stop", "auto-gate", f"BLOCKED:{','.join(failed)}")
        print("", file=sys.stderr)
        print(f"🚫 Auto Gate BLOCKED. Failures: {', '.join(failed)}", file=sys.stderr)
        print("", file=sys.stderr)
        print("=== INSTRUCTIONS FOR AI AGENT ===", file=sys.stderr)
        print("DO NOT STOP. You MUST fix the errors above and try again.", file=sys.stderr)
        print("Step 1: Read each ❌ error message above carefully.", file=sys.stderr)
        print("Step 2: Fix the code that caused each failure.", file=sys.stderr)
        print("Step 3: After fixing, the gate will re-run automatically.", file=sys.stderr)
        print("=================================", file=sys.stderr)
        sys.exit(2)

    hook_log("Stop", "auto-gate", "PASS")
    print(f"✅ Auto Gate passed ({len(py_files)} file(s) checked)")
    sys.exit(0)


if __name__ == "__main__":
    main()
