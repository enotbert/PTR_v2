"""Workspace path sandbox helpers."""

from __future__ import annotations

from pathlib import Path


class PathEscapeError(ValueError):
    """Raised when a user-supplied path leaves the workspace root."""


def resolve_under_root(root: Path, user_path: str) -> Path:
    """
    Resolve ``user_path`` (relative to ``root``) and ensure the result stays
    under ``root`` after resolving symlinks.

    Rejects absolute ``user_path`` values and traversal attempts like ``../``.
    """

    root_resolved = root.resolve()
    raw = Path(user_path)
    if raw.is_absolute():
        raise PathEscapeError("absolute paths are not allowed for workspace tools")

    candidate = (root_resolved / raw).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:  # pragma: no cover - defensive
        raise PathEscapeError("path escapes workspace root") from exc
    return candidate
