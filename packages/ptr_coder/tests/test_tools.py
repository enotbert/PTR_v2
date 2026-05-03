from pathlib import Path

from ptr_coder.tools import execute_tool


def test_read_write_roundtrip(tmp_path: Path) -> None:
    root = tmp_path
    out = execute_tool(
        root=root,
        name="write_file",
        arguments_json='{"path": "sub/x.txt", "content": "hello"}',
    )
    assert "OK:" in out
    text = execute_tool(
        root=root,
        name="read_file",
        arguments_json='{"path": "sub/x.txt"}',
    )
    assert text == "hello"


def test_list_directory(tmp_path: Path) -> None:
    root = tmp_path
    (root / "a").mkdir()
    (root / "b.txt").write_text("z", encoding="utf-8")
    listing = execute_tool(
        root=root,
        name="list_directory",
        arguments_json='{"path": "."}',
    )
    assert "a" in listing.splitlines()
    assert "b.txt" in listing.splitlines()


def test_execute_tool_bad_json(tmp_path: Path) -> None:
    out = execute_tool(root=tmp_path, name="read_file", arguments_json="{")
    assert out.startswith("ERROR: invalid JSON")


def test_execute_unknown_tool(tmp_path: Path) -> None:
    out = execute_tool(root=tmp_path, name="nope", arguments_json="{}")
    assert "unknown tool" in out


def test_path_escape(tmp_path: Path) -> None:
    out = execute_tool(
        root=tmp_path,
        name="read_file",
        arguments_json='{"path": "../outside.txt"}',
    )
    assert out.startswith("ERROR:")
    assert "workspace" in out.lower() or "absolute" in out.lower()
