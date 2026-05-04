---
name: invoke-ptr-coder
description: Run one ptr_coder iteration against an existing handoff under .ai/handoffs/. Use when delegating coding work from Cursor to the local LM Studio adapter per .ai/rules/70-orchestration-ptr-coder.md, or when the user asks to invoke ptr_coder, ptr-coder, or the Python coder adapter.
---

# invoke-ptr-coder

Single-iteration Cursor → **ptr_coder** delegation. Reads a handoff, runs `python -m ptr_coder` with the repo root, captures stdout/stderr and git diff, then Cursor fills `## Result` and validates against `## Commands` / acceptance criteria.

## When to use

- Handoff `.ai/handoffs/PTR-XXX-<slug>.md` exists and passes `bash scripts/validate-handoff.sh <file>`.
- User says "delegate to ptr_coder", "run ptr_coder", "invoke the LM adapter", or similar.

Do **not** use this skill to *author* a handoff from scratch (future skill: `prepare-ptr-coder-handoff`).

## Pre-flight

- [ ] Feature branch `PTR-XXX-<slug>` (not `main`).
- [ ] Working tree clean except intentional edits (handoff, etc.).
- [ ] Handoff path correct; all nine required `##` sections present ([`70-orchestration-ptr-coder.md`](../../../.ai/rules/70-orchestration-ptr-coder.md)).
- [ ] **LM Studio up:** `curl` to `http://localhost:1234/v1/models` (or your `PTR_CODER_BASE_URL` origin + `/v1/models`) returns **200** and lists `PTR_CODER_MODEL`.
- [ ] `pip install -e "./packages/ptr_coder[dev]"` (or equivalent) so `python -m ptr_coder` works.

If any check fails — stop and tell the user what to fix.

## Workflow checklist

```
- [ ] Step 1: Read handoff
- [ ] Step 2: Build ptr_coder command (env + flags)
- [ ] Step 3: Run ptr_coder (real subprocess)
- [ ] Step 4: Capture stdout/stderr + git status
- [ ] Step 5: Fill ## Result in handoff
- [ ] Step 6: Independent validation (Commands section)
- [ ] Step 7: Decide next iteration or PR
```

### Step 2 — Canonical command

From repo root ([ADR-0006](../../../docs/adr/0006-python-lmstudio-coder-adapter.md)):

```bash
python -m ptr_coder \
  --handoff ".ai/handoffs/PTR-XXX-<slug>.md" \
  --root "." \
  --max-iterations 32 \
  --cancel-file ".ptr_coder_cancel"
```

Substitute the real handoff filename. Optionally export `PTR_CODER_BASE_URL`, `PTR_CODER_MODEL`, `PTR_CODER_API_KEY`, `PTR_CODER_REQUEST_TIMEOUT_SEC` before running. Omit `--cancel-file` if you only rely on Ctrl+C to cancel.

### Step 3 — Run

Use the Shell tool from repo root. LM inference can take **minutes** — use a generous `block_until_ms` (e.g. 300000).

### Step 4–5 — Capture

- Record exit code; **follow stderr live**: ptr_coder prints `[ptr_coder]` lines (iteration, response time, tool names) so long LM calls are visible.
- **Cancel a hung run:** ask the user to **Ctrl+C**, or create the file passed as `--cancel-file` (e.g. orchestrator `touch .ptr_coder_cancel` if that path was agreed). Exit code **130** means cooperative cancel. For stuck HTTP only, use **`PTR_CODER_REQUEST_TIMEOUT_SEC`** (see `packages/ptr_coder/README.md`).
- `git status --short`, `git diff` for scope audit.
- Append **`## Result`** (or `## Result (Iteration N)`) in the handoff — **Cursor** writes this; ptr_coder does not edit the handoff file.

### Step 6 — Validation

Run every command from `## Commands` yourself. Do not trust the model’s self-report alone.

### Step 7 — Next step

| Outcome | Action |
|---|---|
| Green + scope clean | Stop; suggest PR / Linear **In Review**. |
| Partial / scope drift | Add `## Iteration N+1` with corrections; re-run (max **2** retries before escalate). |
| Blocked | Linear **Blocked**, PR Draft, summarize for human. |

## Related

- Protocol: [`.ai/rules/70-orchestration-ptr-coder.md`](../../../.ai/rules/70-orchestration-ptr-coder.md)
- Personas: [`.ai/rules/65-personas.md`](../../../.ai/rules/65-personas.md)
- Package: [`packages/ptr_coder/README.md`](../../../packages/ptr_coder/README.md)
