---
name: invoke-codex
description: Run a single iteration of Codex CLI as a subprocess against an existing handoff file under .ai/handoffs/. Use when delegating coding work from Cursor to Codex CLI per the orchestration protocol in .ai/rules/70-orchestration-codex-cli.md, or when the user asks to invoke, run, or call Codex on a handoff.
---

# invoke-codex

Single-iteration Cursor → Codex CLI delegation. Reads an existing handoff, formulates the command, runs it, captures the result back into the handoff, and validates against acceptance criteria.

## When to use

- A handoff file `.ai/handoffs/PTR-XXX-<slug>.md` exists and is filled (Goal, Files in scope, Acceptance criteria, Test plan, Persona, Commands).
- The user says "delegate this", "run codex", "invoke codex", "hand off to codex", or similar.
- A previous iteration left an `## Iteration N` section with feedback to address.

Do **not** use this skill to *create* a handoff. Handoff creation is a separate task (future skill: `prepare-codex-handoff`).

## Pre-flight checklist

Before running anything, verify:

- [ ] We are on a feature branch named `PTR-XXX-<slug>` (not on `main`)
- [ ] Working tree is clean (`git status` shows no unstaged changes outside the handoff file)
- [ ] Handoff file exists at `.ai/handoffs/PTR-XXX-<slug>.md`
- [ ] Handoff has a `## Persona` section naming a known persona from `.ai/rules/65-personas.md`
- [ ] Handoff has a `## Commands` section with at least Lint / Test commands
- [ ] **Codex CLI runtime is up.** Per [ADR-0005](../../../docs/adr/0005-codex-cli-local-runtime.md): LM Studio is running, Local Server is on, the model from `CODEX_MODEL` (default `qwen3-coder-30b-a3b-instruct`) is **loaded in memory**, and `curl <CODEX_HOST>/v1/models` (default host `http://localhost:1234`) returns 200 with the model in the list.

If any check fails — stop and ask the user. For the runtime check, surface the specific failure (LM Studio down vs model not loaded vs different model loaded) so the user can fix it in one step.

## Workflow

Track progress with this checklist:

```
- [ ] Step 1: Read handoff
- [ ] Step 2: Build invocation
- [ ] Step 3: Run Codex CLI
- [ ] Step 4: Capture result
- [ ] Step 5: Independent validation
- [ ] Step 6: Decide next iteration
```

### Step 1: Read handoff

Read the entire handoff file. Verify presence of all required sections per `.ai/rules/70-orchestration-codex-cli.md`:

- `## Goal`
- `## Context`
- `## Files in scope`
- `## Out of scope`
- `## Acceptance criteria`
- `## Test plan`
- `## Persona`
- `## Constraints`
- `## Commands`

If sections are missing — stop, ask user to complete the handoff or fix it inline.

### Step 2: Build invocation

Runtime, model and host are fixed in [ADR-0005](../../../docs/adr/0005-codex-cli-local-runtime.md): LM Studio @ `http://localhost:1234`, model `qwen3-coder-30b-a3b-instruct`, both overridable via env vars `CODEX_HOST` and `CODEX_MODEL`. Full canonical command and prerequisites are in [`.ai/rules/70-orchestration-codex-cli.md`](../../../.ai/rules/70-orchestration-codex-cli.md).

#### Canonical command

POSIX shell:

```bash
codex --oss \
  --model "${CODEX_MODEL:-qwen3-coder-30b-a3b-instruct}" \
  --host "${CODEX_HOST:-http://localhost:1234}"
```

PowerShell (Windows dev box):

```powershell
$model     = if ($env:CODEX_MODEL) { $env:CODEX_MODEL } else { "qwen3-coder-30b-a3b-instruct" }
$codexHost = if ($env:CODEX_HOST)  { $env:CODEX_HOST }  else { "http://localhost:1234" }
codex --oss --model $model --host $codexHost
```

#### Handoff delivery

The exact flag for handing the spec file to Codex CLI (`--instructions <file>`, stdin redirect, or other) is **not yet pinned** — it depends on the installed Codex CLI version and will be locked in on the **first real delegation**. Until then:

1. Run `codex --help` once to discover the supported handoff flag for the current version.
2. Append the chosen flag to the canonical command. Examples (pick whichever the CLI actually supports):

   ```bash
   # If --instructions is supported:
   codex --oss --model "..." --host "..." --instructions .ai/handoffs/PTR-XXX-<slug>.md

   # If stdin is the supported mechanism:
   codex --oss --model "..." --host "..." < .ai/handoffs/PTR-XXX-<slug>.md
   ```

3. After the first successful run, update both [`.ai/rules/70-orchestration-codex-cli.md`](../../../.ai/rules/70-orchestration-codex-cli.md) and this skill with the confirmed flag (small docs PR, no ADR required — this is operational detail).

Substitute `PTR-XXX-<slug>` from the actual handoff filename.

### Step 3: Run Codex CLI

Run the command from the repository root via the Shell tool. Stream output to the user.

If the command requires more than ~120 seconds, set a generous `block_until_ms` and monitor periodically — do not poll reflexively.

If the command fails with non-zero exit:
- Capture the full stderr.
- **Do not retry blindly.** Diagnose first.
- Common causes: handoff path typo, missing model/binary, rate limit, working tree issue.

### Step 4: Capture result

After Codex CLI completes, append (or replace, if blank) the `## Result` section in the handoff file:

```markdown
## Result

- **Started:** <UTC timestamp>
- **Finished:** <UTC timestamp>
- **Exit code:** <code>
- **Files changed:** <bullet list of paths from `git status`>
- **Tests run by Codex:** <list with pass/fail>
- **Issues out of scope (not modified):** <list with description, see Out of scope>
- **Notes:** <any deviations from spec, requests for clarification>
```

If iteration N > 0, name it `## Result (Iteration N)` and keep prior iterations.

### Step 5: Independent validation

Run all commands listed in the handoff `## Commands` section yourself, regardless of what Codex reported. Treat its self-report as a hint, not as truth.

For each command:
- Run with `Shell` tool.
- Record actual exit code and key output in the `## Validation` subsection of `## Result`.

Then compare the diff (`git diff main..HEAD`) against `## Files in scope` and `## Out of scope`:

- Any change outside `Files in scope` must be explained or reverted.
- Any change in `Out of scope` is a violation — flag prominently.

### Step 6: Decide next iteration

Compare result against `## Acceptance criteria`:

| Outcome | Next action |
|---|---|
| All criteria met, validation green, scope clean | Stop. Report success to user. Suggest moving to PR (use `linear-flow` skill to mark `In Review`, then `gh pr create`). |
| Criteria partially met or scope drift | Add `## Iteration N+1 — Refinement` section to handoff with pointed corrections; re-run from Step 2. Hard limit: **2 retries** before escalation. |
| Criteria not met after 2 iterations | Stop. Mark Linear issue `Blocked`, set PR (if any) to Draft, summarize blocker for user. |
| Codex returned "needs clarification" in Result notes | Stop. Surface the question to the user; do not guess. |

## Output report (to the user)

After the skill completes (success or escalation), produce a short summary:

- Handoff: `.ai/handoffs/PTR-XXX-<slug>.md`
- Persona: `<name>`
- Iteration: `<N>`
- Files changed: `<count>`
- Validation: `<pass/fail per command>`
- Outcome: `<Success | Iterating | Blocked>`
- Suggested next step: `<one line>`

## Anti-patterns

- ❌ Trusting Codex's self-reported test results without independent run.
- ❌ Running Codex against a stale `main` (always rebase the feature branch first).
- ❌ Allowing scope drift "while we're at it" — out-of-scope changes go to a new task.
- ❌ More than 2 corrective iterations without escalating to user.
- ❌ Editing the handoff to make criteria fit the result (always update result/iteration, never the spec, post-hoc).

## Related

- Protocol: [`.ai/rules/70-orchestration-codex-cli.md`](../../../.ai/rules/70-orchestration-codex-cli.md)
- Personas: [`.ai/rules/65-personas.md`](../../../.ai/rules/65-personas.md)
- Linear lifecycle: skill `linear-flow`, rules [`.ai/rules/50-task-management.md`](../../../.ai/rules/50-task-management.md)
