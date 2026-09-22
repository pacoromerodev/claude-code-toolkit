#!/usr/bin/env bash
# Fixture tests for the repository's own CI scripts.
#
# Each checker runs against a tree that must pass and a tree with planted
# faults, and every planted fault must be named in the output.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$HERE/.."
FIXTURES="$HERE/fixtures"
PY="${PYTHON:-python3}"

export PYTHONDONTWRITEBYTECODE=1
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
cd "$SANDBOX" || exit 1

pass=0
fail=0
ok()  { printf 'ok    %-18s %s\n' "$1" "$2"; pass=$((pass + 1)); return 0; }
bad() { printf 'FAIL  %-18s %s\n' "$1" "$2"; fail=$((fail + 1)); return 0; }

# expect_exit <label> <actual> <wanted>
expect_exit() {
  if [[ "$2" == "$3" ]]; then ok "$1" "exit $2"; else bad "$1" "exit $2, wanted $3"; fi
}

# expect_text <label> <output> <substring>
expect_text() {
  if [[ "$2" == *"$3"* ]]; then ok "$1" "reports: $3"; else bad "$1" "does not report: $3"; fi
}

echo "== check_eval_cases.py =="
out="$("$PY" "$SCRIPTS/check_eval_cases.py" "$FIXTURES/eval-cases/good" 2>&1)"
expect_exit "eval-cases good" "$?" 0
out="$("$PY" "$SCRIPTS/check_eval_cases.py" "$FIXTURES/eval-cases/bad" 2>&1)"
expect_exit "eval-cases bad" "$?" 1
expect_text "eval-cases bad" "$out" "prompt-only: uses prompt.md"
expect_text "eval-cases bad" "$out" "untagged-bash: allows Bash but is not tagged needs-bash"
expect_text "eval-cases bad" "$out" "one-run: a positive case runs 1 time(s)"
expect_text "eval-cases bad" "$out" "one-sided/graders/criteria.md: no \"score well\" section"
expect_text "eval-cases bad" "$out" "no-scaffold: scaffold_script 'missing.sh' does not exist"
expect_text "eval-cases bad" "$out" "misnamed: name is 'something-else'"

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
