"""Environment-backed configuration."""

from __future__ import annotations

import pytest

from ptr_coder.config import load_config


def test_request_timeout_unset_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PTR_CODER_REQUEST_TIMEOUT_SEC", raising=False)
    assert load_config().request_timeout_sec is None


def test_request_timeout_zero_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PTR_CODER_REQUEST_TIMEOUT_SEC", "0")
    assert load_config().request_timeout_sec is None


def test_request_timeout_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PTR_CODER_REQUEST_TIMEOUT_SEC", "600")
    assert load_config().request_timeout_sec == 600.0
