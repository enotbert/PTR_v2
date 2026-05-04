"""Environment-backed configuration for ptr_coder."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _request_timeout_from_env() -> Optional[float]:
    """
    Per-request HTTP timeout for the OpenAI client (single float, seconds).
    Unset, empty, or "0" => no client-level timeout (may hang until TCP stack).
    """

    raw = os.environ.get("PTR_CODER_REQUEST_TIMEOUT_SEC", "").strip()
    if not raw or raw == "0":
        return None
    return float(raw)


@dataclass(frozen=True)
class CoderConfig:
    """Runtime settings resolved from environment variables."""

    base_url: str
    model: str
    api_key: str
    request_timeout_sec: Optional[float]


def load_config() -> CoderConfig:
    """Load configuration using ADR-0006 defaults."""

    return CoderConfig(
        base_url=os.environ.get("PTR_CODER_BASE_URL", "http://localhost:1234/v1"),
        model=os.environ.get("PTR_CODER_MODEL", "qwen3-coder-30b-a3b-instruct"),
        api_key=os.environ.get("PTR_CODER_API_KEY", "lm-studio"),
        request_timeout_sec=_request_timeout_from_env(),
    )
