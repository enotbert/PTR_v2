"""Command-line entrypoint for ptr_coder."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ptr_coder.agent import build_openai_client, read_handoff_file, run_agent
from ptr_coder.config import load_config


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
    args = parser.parse_args(argv)

    handoff_path = Path(args.handoff)
    if not handoff_path.is_file():
        print(f"error: handoff is not a file: {handoff_path}", file=sys.stderr)
        return 2

    root = Path(args.root)
    cfg = load_config()

    try:
        text = read_handoff_file(handoff_path)
        client = build_openai_client(cfg.base_url, cfg.api_key)
        result = run_agent(
            client=client,
            model=cfg.model,
            root=root,
            handoff_text=text,
            max_iterations=args.max_iterations,
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
