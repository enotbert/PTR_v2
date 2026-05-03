from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

from ptr_coder.agent import run_agent


def _msg(
    *,
    content: Optional[str] = None,
    tool_calls: Optional[List[SimpleNamespace]] = None,
) -> SimpleNamespace:
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _resp(message: SimpleNamespace) -> SimpleNamespace:
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice])


class _FakeCompletions:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = responses

    def create(self, **_kwargs: Any) -> SimpleNamespace:
        return self._responses.pop(0)


class _FakeChat:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.completions = _FakeCompletions(responses)


class FakeClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.chat = _FakeChat(responses)


def test_agent_runs_tool_then_finishes(tmp_path: Path) -> None:
    root = tmp_path
    tc_write = SimpleNamespace(
        id="call-1",
        type="function",
        function=SimpleNamespace(
            name="write_file",
            arguments='{"path": "out.txt", "content": "done"}',
        ),
    )
    first = _resp(_msg(content=None, tool_calls=[tc_write]))
    second = _resp(_msg(content="All set.", tool_calls=None))
    client = FakeClient([first, second])

    result = run_agent(
        client=client,
        model="fake-model",
        root=root,
        handoff_text="Write out.txt with content done.",
        max_iterations=5,
    )
    assert result.exit_code == 0
    assert (root / "out.txt").read_text(encoding="utf-8") == "done"
    assert result.final_text == "All set."


def test_agent_max_iterations(tmp_path: Path) -> None:
    root = tmp_path
    tc = SimpleNamespace(
        id="call-loop",
        type="function",
        function=SimpleNamespace(
            name="list_directory",
            arguments='{"path": "."}',
        ),
    )
    repeating = _resp(_msg(content=None, tool_calls=[tc]))
    client = FakeClient([repeating, repeating, repeating])

    result = run_agent(
        client=client,
        model="fake-model",
        root=root,
        handoff_text="List files forever.",
        max_iterations=2,
    )
    assert result.exit_code == 1
    assert result.final_text is not None
    assert "max_iterations_exceeded" in result.final_text
