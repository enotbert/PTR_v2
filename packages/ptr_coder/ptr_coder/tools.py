"""Built-in function tools (LM Studio-compatible JSON schemas only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ptr_coder.paths import PathEscapeError, resolve_under_root

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file under the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write UTF-8 text to a path under the workspace root (creates parent dirs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file contents to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List immediate children of a directory under the workspace root (non-recursive).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path; use '.' for workspace root.",
                    },
                },
                "required": ["path"],
            },
        },
    },
]


def _tool_read_file(root: Path, path: str) -> str:
    target = resolve_under_root(root, path)
    if not target.is_file():
        return f"ERROR: not a file: {path}"
    return target.read_text(encoding="utf-8", errors="replace")


def _tool_write_file(root: Path, path: str, content: str) -> str:
    target = resolve_under_root(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content.encode('utf-8'))} bytes to {path}"


def _tool_list_directory(root: Path, path: str) -> str:
    target = resolve_under_root(root, path)
    if not target.is_dir():
        return f"ERROR: not a directory: {path}"
    names = sorted(p.name for p in target.iterdir())
    return "\n".join(names) if names else "(empty)"


def execute_tool(*, root: Path, name: str, arguments_json: str) -> str:
    """Dispatch a tool by name; returns a string passed back to the model."""

    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON arguments: {exc}"

    try:
        if name == "read_file":
            rel = str(args.get("path", ""))
            return _tool_read_file(root, rel)
        if name == "write_file":
            rel = str(args.get("path", ""))
            content = str(args.get("content", ""))
            return _tool_write_file(root, rel, content)
        if name == "list_directory":
            rel = str(args.get("path", "."))
            return _tool_list_directory(root, rel)
        return f"ERROR: unknown tool {name!r}"
    except PathEscapeError as exc:
        return f"ERROR: {exc}"
    except OSError as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"
