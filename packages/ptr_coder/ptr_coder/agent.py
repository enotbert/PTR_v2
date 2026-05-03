"""Agent loop: chat.completions + function tools only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from ptr_coder.tools import TOOL_DEFINITIONS, execute_tool


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


def run_agent(
    *,
    client: Any,
    model: str,
    root: Path,
    handoff_text: str,
    max_iterations: int,
) -> AgentResult:
    """
    Run the tool-agent loop until the model stops without tool calls or the
    iteration budget is exhausted.

    ``handoff_text`` is treated as the primary user instruction payload.
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

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=cast(Any, TOOL_DEFINITIONS),
            tool_choice="auto",
        )
        choice = response.choices[0]
        message = choice.message
        messages.append(_assistant_message_dict(message))

        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            last_text = message.content or ""
            return AgentResult(exit_code=0, final_text=last_text)

        for tc in tool_calls:
            name = tc.function.name
            args = tc.function.arguments or "{}"
            output = execute_tool(root=root, name=name, arguments_json=args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output,
                }
            )

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


def build_openai_client(base_url: str, api_key: str) -> Any:
    """Construct the real OpenAI-compatible SDK client."""

    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=api_key)
