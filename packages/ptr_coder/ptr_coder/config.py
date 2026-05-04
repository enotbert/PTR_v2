"""Environment-backed configuration for ptr_coder."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CoderConfig:
    """Runtime settings resolved from environment variables."""

    base_url: str
    model: str
    api_key: str


def load_config() -> CoderConfig:
    """Load configuration using ADR-0006 defaults."""

    return CoderConfig(
        base_url=os.environ.get("PTR_CODER_BASE_URL", "http://localhost:1234/v1"),
        model=os.environ.get("PTR_CODER_MODEL", "qwen3-coder-30b-a3b-instruct"),
        api_key=os.environ.get("PTR_CODER_API_KEY", "lm-studio"),
    )
