#!/usr/bin/env bash
#
# test-validate-handoff.sh — plain-bash test runner for validate-handoff.sh.
#
# No external test framework (no bats, no shunit2). Bash 3.2+ compatible.
# Exit 0 if all tests pass, 1 otherwise. Prints PASS/FAIL per test and
# a final RESULT: <passed>/<total> passed line.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VALIDATOR="${SCRIPT_DIR}/../validate-handoff.sh"
FIXTURES="${SCRIPT_DIR}/fixtures"

PASSED=0
TOTAL=0

TMP_OUT="$(mktemp)"
TMP_ERR="$(mktemp)"
trap 'rm -f "$TMP_OUT" "$TMP_ERR"' EXIT

# RC is a global set by run_validator with the validator's exit code.
RC=0
run_validator() {
  RC=0
  bash "$VALIDATOR" "$@" >"$TMP_OUT" 2>"$TMP_ERR" || RC=$?
}

pass() {
  TOTAL=$((TOTAL + 1))
  PASSED=$((PASSED + 1))
  printf 'PASS %s\n' "$1"
}

fail() {
  TOTAL=$((TOTAL + 1))
  printf 'FAIL %s: %s\n' "$1" "$2"
  if [ -s "$TMP_OUT" ]; then printf '  stdout: %s\n' "$(cat "$TMP_OUT")"; fi
  if [ -s "$TMP_ERR" ]; then printf '  stderr: %s\n' "$(cat "$TMP_ERR")"; fi
}

# --- tests ---

# 1. Valid handoff: exit 0, stdout has OK:.
NAME='valid-handoff exits 0 with OK:'
run_validator "$FIXTURES/valid-handoff.md"
if [ "$RC" -eq 0 ] && grep -q '^OK:' "$TMP_OUT"; then
  pass "$NAME"
else
  fail "$NAME" "expected exit=0 with OK: prefix on stdout, got exit=$RC"
fi

# 2. Missing-section handoff: exit 1, stderr has MISSING: ## Persona.
NAME='missing-section exits 1 with MISSING: ## Persona'
run_validator "$FIXTURES/missing-section.md"
if [ "$RC" -eq 1 ] && grep -qx 'MISSING: ## Persona' "$TMP_ERR"; then
  pass "$NAME"
else
  fail "$NAME" "expected exit=1 and MISSING: ## Persona on stderr, got exit=$RC"
fi

# 3. Whitespace-headers: exit 0 (trailing/leading whitespace tolerated).
NAME='whitespace-headers exits 0'
run_validator "$FIXTURES/whitespace-headers.md"
if [ "$RC" -eq 0 ] && grep -q '^OK:' "$TMP_OUT"; then
  pass "$NAME"
else
  fail "$NAME" "expected exit=0, got exit=$RC"
fi

# 4. Empty file: exit 1, exactly 9 MISSING: lines.
NAME='empty exits 1 with all 9 MISSING:'
run_validator "$FIXTURES/empty.md"
actual_count=0
if [ "$RC" -eq 1 ]; then
  actual_count=$(grep -c '^MISSING:' "$TMP_ERR" || true)
fi
if [ "$RC" -eq 1 ] && [ "$actual_count" -eq 9 ]; then
  pass "$NAME"
else
  fail "$NAME" "expected exit=1 and 9 MISSING: lines, got exit=$RC and $actual_count lines"
fi

# 5. Nonexistent file: exit 2.
NAME='nonexistent file exits 2'
run_validator "/nonexistent/handoff-xyz-does-not-exist.md"
if [ "$RC" -eq 2 ]; then
  pass "$NAME"
else
  fail "$NAME" "expected exit=2, got exit=$RC"
fi

# 6. No arguments: exit 2.
NAME='no arguments exits 2'
run_validator
if [ "$RC" -eq 2 ]; then
  pass "$NAME"
else
  fail "$NAME" "expected exit=2, got exit=$RC"
fi

# --- summary ---

printf 'RESULT: %d/%d passed\n' "$PASSED" "$TOTAL"
if [ "$PASSED" -eq "$TOTAL" ]; then
  exit 0
fi
exit 1
