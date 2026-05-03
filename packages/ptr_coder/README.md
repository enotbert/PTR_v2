# ptr_coder

Python adapter that runs a **minimal function-tool agent loop** against an OpenAI-compatible chat endpoint (for example **LM Studio** local server). It replaces Codex CLI as the repo coding executor; see [ADR-0006](../../docs/adr/0006-python-lmstudio-coder-adapter.md).

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
| `PTR_CODER_MODEL` | `gemma-4-26b-a4b-it` | Model id known to the server |
| `PTR_CODER_API_KEY` | `lm-studio` | Bearer token string (LM Studio accepts arbitrary local keys) |

Copy [`.env.example`](../../.env.example) to `.env.local` (gitignored) and adjust without touching the repo.

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
