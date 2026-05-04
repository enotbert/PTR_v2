"""Progress lines to stderr (orchestrator-visible, unbuffered)."""

from __future__ import annotations

import sys
from typing import TextIO


def log_line(message: str, *, stream: TextIO = sys.stderr) -> None:
    """Write one UTF-8 line to stderr and flush (visible in Cursor terminal immediately)."""

    print(f"[ptr_coder] {message}", file=stream, flush=True)
