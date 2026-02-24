"""Sandboxed path helpers for filesystem tools."""

import os
from pathlib import Path


def get_workdir() -> Path:
    """Return the configured sandbox root directory."""
    # All filesystem tools operate relative to this directory.
    root = Path(os.getenv("AGENT_WORKDIR", ".")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_in_workdir(user_path: str) -> Path:
    """Resolve a user path safely inside the sandbox root."""
    # Reject absolute paths so callers cannot bypass sandbox rules.
    candidate = Path(user_path)
    if candidate.is_absolute():
        raise ValueError("Use relative paths only.")

    root = get_workdir()
    resolved = (root / candidate).resolve()

    # Ensure final resolved path is the root or a child of root.
    if resolved != root and root not in resolved.parents:
        raise ValueError("Cannot access paths outside the working directory.")

    return resolved


def to_relative_display(path: Path) -> str:
    """Format a path relative to sandbox root for user-facing messages."""
    root = get_workdir()
    try:
        rel = path.resolve().relative_to(root)
        rel_str = str(rel)
        return "." if rel_str == "." else rel_str
    except Exception:
        return str(path)
