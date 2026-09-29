#!/usr/bin/env bash
# Fixture tests for the regulated-delivery hook.
#
# Each case feeds a payload from fixtures/ to guard_pii.py and asserts the exit
# code, and where it matters a substring of stderr. Exit 2 means the hook
# blocked; anything else means it let the call through.
#
# Run: plugins/regulated-delivery/tests/run.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$HERE/../scripts"
FIXTURES="$HERE/fixtures"
PY="${PYTHON:-python3}"

# Run from a throwaway directory, without bytecode, so nothing is left in the
# repository. `allowed/` is the project whose exception list allows one value.
export PYTHONDONTWRITEBYTECODE=1
unset CLAUDE_PROJECT_DIR
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
cd "$SANDBOX" || exit 1
mkdir -p allowed/.claude
printf '# test data the team agreed on\n^ES6000491500051234567892$\n' > allowed/.claude/pii-guard-allow

pass=0
fail=0

# check <fixture> <expected exit> [expected stderr substring]
check() {
  local fixture="$1" want="$2" needle="${3:-}"
  local out code
  out="$("$PY" "$SCRIPTS/guard_pii.py" < "$FIXTURES/$fixture" 2>&1)"
  code=$?
  if [[ "$code" != "$want" ]]; then
    printf 'FAIL  %-30s exit %s, wanted %s\n' "$fixture" "$code" "$want"
    [[ -n "$out" ]] && printf '        output: %s\n' "${out%%$'\n'*}"
    fail=$((fail + 1))
    return
  fi
  if [[ -n "$needle" && "$out" != *"$needle"* ]]; then
    printf 'FAIL  %-30s exit %s but stderr lacks %q\n' "$fixture" "$code" "$needle"
    fail=$((fail + 1))
    return
  fi
  printf 'ok    %s\n' "$fixture"
  pass=$((pass + 1))
}

echo "== guard_pii: must block =="
check pii-iban-write.json       2 "an IBAN (ES60…7892)"
check pii-card-edit.json        2 "Visa card number"
check pii-dni-notebook.json     2 "DNI"
check pii-nie-multiedit.json    2 "NIE"
check pii-allow-file.json       2 "exception list"

echo
echo "== guard_pii: must pass =="
check pii-published-examples.json 0
check pii-bad-checksum.json     0
check pii-plain-numbers.json    0
check pii-allowlisted.json      0
check pii-bash.json             0
check pii-no-input.json         0
check pii-malformed.json        0

# The message names the kind and never repeats the value it found.
out="$("$PY" "$SCRIPTS/guard_pii.py" < "$FIXTURES/pii-iban-write.json" 2>&1)"
if [[ "$out" != *"ES6000491500051234567892"* && "$out" != *"0049 1500 0512 3456"* ]]; then
  printf 'ok    %s\n' "the block message masks the value"
  pass=$((pass + 1))
else
  printf 'FAIL  %s\n' "the block message repeats the value it found"
  fail=$((fail + 1))
fi

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
