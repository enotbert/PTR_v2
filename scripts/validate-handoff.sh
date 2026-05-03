#!/usr/bin/env bash
#
# validate-handoff.sh — verify that a handoff markdown file contains
# all nine required section headers per
# .ai/rules/70-orchestration-ptr-coder.md (nine canonical section headers).
#
# Spec: .ai/handoffs/PTR-6-handoff-validator.md
#
# Usage: validate-handoff.sh <path-to-handoff.md>
#
# Exit codes:
#   0 — all required sections present
#   1 — one or more required sections missing
#   2 — usage error (no argument, missing/non-file path)
#
# Output:
#   exit 0 → stdout: "OK: all required sections present in <path>"
#   exit 1 → stderr: "MISSING: <header>" per missing section, in spec order
#   exit 2 → stderr: "Usage: validate-handoff.sh <path-to-handoff.md>"
#
# Constraints (per handoff): bash 3.2+, no external deps beyond
# coreutils + awk + grep, no network, read-only.

set -euo pipefail

REQUIRED_SECTIONS=(
  "## Goal"
  "## Context"
  "## Files in scope"
  "## Out of scope"
  "## Persona"
  "## Acceptance criteria"
  "## Test plan"
  "## Constraints"
  "## Commands"
)

usage() {
  printf 'Usage: validate-handoff.sh <path-to-handoff.md>\n' >&2
  exit 2
}

if [ "$#" -ne 1 ]; then
  usage
fi

file="$1"

if [ ! -f "$file" ]; then
  usage
fi

# Check each required section. Match a line that, after stripping leading
# and trailing ASCII whitespace, equals the expected header. Case-sensitive.
# bash 3.2 compatible: no associative arrays, no mapfile.
missing=()
for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! LC_ALL=C awk -v want="$section" '
    {
      line = $0
      sub(/^[ \t\r]+/, "", line)
      sub(/[ \t\r]+$/, "", line)
      if (line == want) { found = 1; exit }
    }
    END { exit !found }
  ' "$file"; then
    missing+=("$section")
  fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  printf 'OK: all required sections present in %s\n' "$file"
  exit 0
fi

for s in "${missing[@]}"; do
  printf 'MISSING: %s\n' "$s" >&2
done
exit 1
