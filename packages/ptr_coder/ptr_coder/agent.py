"""Agent loop: chat.completions + function tools only."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from ptr_coder.progress import log_line
from ptr_coder.tools import TOOL_DEFINITIONS, execute_tool

EXIT_CANCELLED = 130


@dataclass(frozen=True)
class AgentResult:
    """Outcome of a single agent run."""

    exit_code: int
    final_text: Optional[str]


def _assistant_message_dict(message: Any) -> dict[str, Any]:
    """Serialize an SDK assistant message into the wire-format dict."""

    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return payload

    serialized: list[dict[str, Any]] = []
    for tc in tool_calls:
        fn = tc.function
        serialized.append(
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function") or "function",
                "function": {"name": fn.name, "arguments": fn.arguments},
            }
        )
    payload["tool_calls"] = serialized
    return payload


def _cancellation_requested(
    cancel_file: Optional[Path],
    cancel_event: Optional[threading.Event],
) -> bool:
    if cancel_event is not None and cancel_event.is_set():
        return True
    return cancel_file is not None and cancel_file.is_file()


def _clear_cancel_file(cancel_file: Optional[Path]) -> None:
    if cancel_file is None or not cancel_file.is_file():
        return
    try:
        cancel_file.unlink()
    except OSError:
        pass


def _tool_call_log_line(name: str, arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json or "{}")
        if isinstance(args, dict) and "path" in args:
            p = str(args.get("path", ""))
            if len(p) > 96:
                p = p[:93] + "..."
            return f"{name} path={p!r}"
    except json.JSONDecodeError:
        pass
    return name


def run_agent(
    *,
    client: Any,
    model: str,
    root: Path,
    handoff_text: str,
    max_iterations: int,
    cancel_file: Optional[Path] = None,
    cancel_event: Optional[threading.Event] = None,
    log_progress: bool = True,
) -> AgentResult:
    """
    Run the tool-agent loop until the model stops without tool calls or the
    iteration budget is exhausted.

    ``handoff_text`` is treated as the primary user instruction payload.

    Cancellation: set ``cancel_event`` (e.g. SIGINT) or create ``cancel_file``
    on disk; checked before each model request and after each response, and
    between tool calls. Exit code 130 means cancelled by orchestrator/user.

    Progress (iteration, timing, tool names) is written to stderr when
    ``log_progress`` is True.
    """

    system = (
        "You are the PTR repo coding agent. Follow the handoff precisely. "
        "Use the provided tools to read and modify files under the workspace root. "
        "Prefer small, focused edits. If the handoff only asks for analysis, respond "
        "without tools. Never invent paths outside the workspace."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": "Execute this handoff:\n\n" + handoff_text,
        },
    ]

    last_text: Optional[str] = None

    for i in range(max_iterations):
        it = i + 1
        if _cancellation_requested(cancel_file, cancel_event):
            _clear_cancel_file(cancel_file)
            if log_progress:
                log_line("cancel: stopping (signal or cancel file)")
            return AgentResult(
                exit_code=EXIT_CANCELLED,
                final_text=json.dumps(
                    {"error": "cancelled", "phase": "before_model_request"}
                ),
            )

        if log_progress:
            log_line(f"iteration {it}/{max_iterations}: requesting model completion...")

        t0 = time.monotonic()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=cast(Any, TOOL_DEFINITIONS),
            tool_choice="auto",
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        choice = response.choices[0]
        message = choice.message
        messages.append(_assistant_message_dict(message))

        tool_calls = getattr(message, "tool_calls", None) or []

        if log_progress:
            if tool_calls:
                log_line(
                    f"iteration {it}/{max_iterations}: response in {elapsed_ms}ms "
                    f"({len(tool_calls)} tool call(s))"
                )
            else:
                log_line(
                    f"iteration {it}/{max_iterations}: response in {elapsed_ms}ms "
                    "(final assistant message, no tools)"
                )

        if _cancellation_requested(cancel_file, cancel_event):
            _clear_cancel_file(cancel_file)
            if log_progress:
                log_line("cancel: stopping after model response")
            return AgentResult(
                exit_code=EXIT_CANCELLED,
                final_text=json.dumps(
                    {"error": "cancelled", "phase": "after_model_response"}
                ),
            )

        if not tool_calls:
            last_text = message.content or ""
            return AgentResult(exit_code=0, final_text=last_text)

        for tc in tool_calls:
            if _cancellation_requested(cancel_file, cancel_event):
                _clear_cancel_file(cancel_file)
                if log_progress:
                    log_line("cancel: stopping before running remaining tools")
                return AgentResult(
                    exit_code=EXIT_CANCELLED,
                    final_text=json.dumps(
                        {"error": "cancelled", "phase": "before_tool_execution"}
                    ),
                )

            name = tc.function.name
            args = tc.function.arguments or "{}"
            if log_progress:
                log_line(f"tool {_tool_call_log_line(name, args)}")
            output = execute_tool(root=root, name=name, arguments_json=args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output,
                }
            )

    if log_progress:
        log_line(f"stopped: max_iterations ({max_iterations}) exceeded")
    return AgentResult(
        exit_code=1,
        final_text=json.dumps(
            {
                "error": "max_iterations_exceeded",
                "max_iterations": max_iterations,
            }
        ),
    )


def read_handoff_file(path: Path) -> str:
    """Read UTF-8 handoff contents from disk."""

    return path.read_text(encoding="utf-8", errors="replace")


def build_openai_client(
    base_url: str,
    api_key: str,
    *,
    timeout: Optional[float] = None,
) -> Any:
    """Construct the real OpenAI-compatible SDK client."""

    from openai import OpenAI

    kwargs: dict[str, Any] = {"base_url": base_url, "api_key": api_key}
    if timeout is not None:
        kwargs["timeout"] = timeout
    return OpenAI(**kwargs)
