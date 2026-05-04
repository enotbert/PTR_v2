# ptr_coder

Python adapter that runs a **minimal function-tool agent loop** against an OpenAI-compatible chat endpoint (for example **LM Studio** local server). It replaces Codex CLI as the repo coding executor; see [ADR-0006](../../docs/adr/0006-python-lmstudio-coder-adapter.md). Orchestration protocol for Cursor: [`.ai/rules/70-orchestration-ptr-coder.md`](../../.ai/rules/70-orchestration-ptr-coder.md).

## Requirements

- Python 3.9+ (CI uses 3.12)
- LM Studio (or compatible server) exposing `http://localhost:1234/v1` by default

## Install (editable, from monorepo root)

```bash
pip install -e "./packages/ptr_coder[dev]"
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `PTR_CODER_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible API base URL |
| `PTR_CODER_MODEL` | `qwen3-coder-30b-a3b-instruct` | Model id known to the server |
| `PTR_CODER_API_KEY` | `lm-studio` | Bearer token string (LM Studio accepts arbitrary local keys) |
| `PTR_CODER_REQUEST_TIMEOUT_SEC` | unset / `0` = off | Per-request HTTP timeout (seconds) for `chat.completions`; avoids hangs at the socket layer |

Copy variable names from [`.env.development.example`](../../.env.development.example) (section ptr_coder; see also root [`.env.example`](../../.env.example)) into `.env.local` (gitignored) or your shell and adjust without committing.

## CLI

```bash
python -m ptr_coder --handoff .ai/handoffs/PTR-6-handoff-validator.md --root .
```

Or after install:

```bash
ptr-coder --handoff path/to/handoff.md --root /path/to/repo
```

Options:

- `--max-iterations` (default `32`) — safety cap on tool rounds.
- `--cancel-file PATH` — if this path exists as a **file**, ptr_coder stops at the next safe point (before a model request, after a response, or between tools). Relative paths are resolved under `--root`. The file is **deleted** when cancellation is honoured. **Orchestrator:** `touch <path>` to request cancel while the process is running.
- `--no-progress` — disable `[ptr_coder]` progress lines on stderr (iteration, timings, tool names).

### Progress (stderr)

Each model round and tool call prints a line to **stderr** with prefix `[ptr_coder]` (unbuffered), for example:

- `iteration 3/32: requesting model completion...`
- `iteration 3/32: response in 4120ms (2 tool call(s))`
- `tool write_file path='apps/foo.txt'`

Final assistant text (when the model finishes without tools) is still printed to **stdout** only.

### Cancellation and interrupts

1. **`--cancel-file`** — orchestrator creates/touches the file; checked before each HTTP completion round and between tools. Exit code **130**.
2. **Ctrl+C (SIGINT)** — same cooperative cancel via an internal flag (exit **130**).

During a **single blocking** `chat.completions` HTTP call, ptr_coder cannot poll the cancel file until the call returns. Combine with **`PTR_CODER_REQUEST_TIMEOUT_SEC`** so a stuck LM Studio request eventually fails and the next check can stop the loop.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success; assistant message on stdout |
| 1 | `max_iterations` exceeded (JSON error on stdout) |
| 130 | Cancelled (SIGINT or cancel file; JSON with `"error": "cancelled"` on stdout) |
| 2 | CLI usage / handoff read error |

## Tools (v1)

Only JSON-schema `function` tools are registered:

- `read_file` — read UTF-8 text under workspace root
- `write_file` — write UTF-8 text (creates parent directories)
- `list_directory` — non-recursive listing

All paths are **relative** to `--root`; absolute paths and path traversal are rejected.

## Tests

```bash
pytest packages/ptr_coder/tests -q
```

Tests mock the OpenAI client and **do not** require a running LM Studio instance.
