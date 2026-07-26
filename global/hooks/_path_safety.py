"""Shared path-safety helpers for global hooks.

Used by check-secrets.py and check-type-suppression.py to prevent
path traversal attacks when inspecting files on disk.
"""

import os
import tempfile


def allowed_roots() -> list[str]:
    """Return filesystem roots this global hook may inspect."""
    roots = [
        os.path.abspath("."),
        os.path.expanduser("~"),
        tempfile.gettempdir(),
        os.path.join(os.sep, "tmp"),
    ]
    for env_name in ("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR", "CODEX_WORKSPACE", "OPENCODE_PROJECT_DIR", "PWD"):
        env_root = os.environ.get(env_name)
        if env_root:
            roots.append(env_root)
    return [os.path.realpath(os.path.abspath(root)) for root in roots]


def is_safe_path(file_path: str) -> bool:
    """Prevent path traversal attacks.  file_path must be inside an allowed root."""
    try:
        real_path = os.path.realpath(os.path.abspath(file_path))
        return any(os.path.commonpath([real_path, root]) == root for root in allowed_roots())
    except (OSError, ValueError):
        return False
