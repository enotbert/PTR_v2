from pathlib import Path

import pytest

from ptr_coder.paths import PathEscapeError, resolve_under_root


def test_resolve_simple(tmp_path: Path) -> None:
    root = tmp_path
    (root / "a.txt").write_text("x", encoding="utf-8")
    got = resolve_under_root(root, "a.txt")
    assert got == (root / "a.txt").resolve()


def test_rejects_absolute(tmp_path: Path) -> None:
    with pytest.raises(PathEscapeError):
        resolve_under_root(tmp_path, str(tmp_path / "evil.txt"))


def test_rejects_parent_escape(tmp_path: Path) -> None:
    (tmp_path / "inside").mkdir()
    with pytest.raises(PathEscapeError):
        resolve_under_root(tmp_path / "inside", "../evil.txt")
