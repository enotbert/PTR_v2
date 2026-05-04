"""Command-line entrypoint for ptr_coder."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path
from typing import List, Optional

from ptr_coder.agent import build_openai_client, read_handoff_file, run_agent
from ptr_coder.config import load_config
from ptr_coder.progress import log_line


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ptr-coder",
        description="Run the PTR coding agent against LM Studio (OpenAI-compatible API).",
    )
    parser.add_argument(
        "--handoff",
        required=True,
        help="Path to a validated handoff markdown file.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Workspace root; all tool paths are relative to this directory.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=32,
        help="Maximum number of model rounds that may emit tool calls.",
    )
    parser.add_argument(
        "--cancel-file",
        default=None,
        metavar="PATH",
        help=(
            "If this path exists as a file, ptr_coder stops at the next safe point "
            "(orchestrator: `touch` / create to request cancel; file is removed when "
            "honored). Use with a path under --root or an absolute path."
        ),
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Do not print iteration / tool progress lines to stderr.",
    )
    args = parser.parse_args(argv)

    handoff_path = Path(args.handoff)
    if not handoff_path.is_file():
        print(f"error: handoff is not a file: {handoff_path}", file=sys.stderr)
        return 2

    root = Path(args.root)
    cfg = load_config()
    log_progress = not args.no_progress
    cancel_path: Optional[Path] = None
    if args.cancel_file:
        cancel_path = Path(args.cancel_file)
        if not cancel_path.is_absolute():
            cancel_path = (root / cancel_path).resolve()

    cancel_event = threading.Event()

    def _on_sigint(*_args: object) -> None:
        cancel_event.set()
        if log_progress:
            log_line(
                "cancel: interrupt (Ctrl+C) - will stop at next safe point "
                "(or remove cancel file if you use --cancel-file)"
            )

    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except ValueError:
        # e.g. not the main thread
        pass

    if log_progress:
        to = cfg.request_timeout_sec
        to_s = f"{to}s" if to is not None else "off (set PTR_CODER_REQUEST_TIMEOUT_SEC)"
        log_line(
            f"start: root={root} model={cfg.model!r} request_timeout={to_s} "
            f"cancel_file={cancel_path!s}"
        )

    try:
        text = read_handoff_file(handoff_path)
        client = build_openai_client(
            cfg.base_url,
            cfg.api_key,
            timeout=cfg.request_timeout_sec,
        )
        result = run_agent(
            client=client,
            model=cfg.model,
            root=root,
            handoff_text=text,
            max_iterations=args.max_iterations,
            cancel_file=cancel_path,
            cancel_event=cancel_event,
            log_progress=log_progress,
        )
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface any SDK/network failure
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if result.final_text:
        print(result.final_text.rstrip())
    return result.exit_code
