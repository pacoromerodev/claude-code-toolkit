#!/usr/bin/env bash
# Fixture tests for the migration checker.
#
# fixtures/unsafe/ plants one unsafe operation per file; fixtures/safe/ holds
# migrations that are genuinely safe during a rolling deploy and must produce
# nothing. The quiet half is the half that decides whether anyone keeps using
# this: a checker that flags safe migrations gets switched off.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$HERE/../scripts/check_migration.py"
FIXTURES="$HERE/fixtures"
PY="${PYTHON:-python3}"

# Run from a throwaway directory, without bytecode: a hook that falls back to
# the current directory, or an imported script writing __pycache__, must never
# leave files in the repository.
export PYTHONDONTWRITEBYTECODE=1
unset CLAUDE_PROJECT_DIR
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
cd "$SANDBOX" || exit 1

pass=0
fail=0

unsafe_output="$("$PY" "$CHECK" "$FIXTURES/unsafe" 2>&1)"
unsafe_code=$?
safe_output="$("$PY" "$CHECK" "$FIXTURES/safe" 2>&1)"
safe_code=$?
liquibase_output="$("$PY" "$CHECK" "$FIXTURES/liquibase" 2>&1)"
liquibase_code=$?

finds() {
  if [[ "$unsafe_output" == *"$2"* ]]; then
    printf 'ok    finds   %s\n' "$1"; ((pass++))
  else
    printf 'FAIL  finds   %s — nothing matched %q\n' "$1" "$2"; ((fail++))
  fi
}

quiet() {
  if [[ "$safe_output" != *"$2"* ]]; then
    printf 'ok    quiet   %s\n' "$1"; ((pass++))
  else
    printf 'FAIL  quiet   %s — safe tree reported %q\n' "$1" "$2"; ((fail++))
  fi
}

code() {
  if [[ "$2" == "$3" ]]; then
    printf 'ok    exit    %s (%s)\n' "$1" "$2"; ((pass++))
  else
    printf 'FAIL  exit    %s — got %s, wanted %s\n' "$1" "$2" "$3"; ((fail++))
  fi
}

echo "== unsafe operations must all be found =="
finds "CREATE INDEX without CONCURRENTLY"  "index-lock"
finds "NOT NULL with no default"           "not-null-no-default"
finds "DROP COLUMN still read by the old version" "drop-column"
finds "RENAME COLUMN"                      "rename-column"
finds "UPDATE with no WHERE"               "unbounded-dml"
finds "duplicate Flyway version"           "duplicate-version"
finds "foreign key validated inline"       "fk-validate"

echo
echo "== the message names the target readably =="
finds "table.column, no stray punctuation"  "orders.legacy_reference"

echo
echo "== safe migrations must produce nothing =="
quiet "new table is not flagged"           "UNSAFE"
quiet "nullable defaulted column is not flagged" "not-null-no-default"
quiet "CONCURRENTLY index is not flagged"  "index-lock"
if [[ "$safe_output" == *"Nothing unsafe found"* ]]; then
  printf 'ok    quiet   reports nothing unsafe\n'; ((pass++))
else
  printf 'FAIL  quiet   did not report clean: %s\n' "${safe_output%%$'\n'*}"; ((fail++))
fi

echo
echo "== liquibase =="
if [[ "$liquibase_output" == *"destructive-change"* ]]; then
  printf 'ok    finds   dropColumn in a changeset\n'; ((pass++))
else
  printf 'FAIL  finds   dropColumn in a changeset\n'; ((fail++))
fi

echo
echo "== exit codes =="
code "unsafe present" "$unsafe_code"    1
code "all safe"       "$safe_code"      0
code "liquibase unsafe" "$liquibase_code" 1

echo
echo "== json output is parseable =="
json_output="$("$PY" "$CHECK" "$FIXTURES/unsafe" --json 2>/dev/null)"
if printf '%s' "$json_output" | "$PY" -c \
   'import json,sys; d=json.load(sys.stdin); assert d["errors"]>0 and d["issues"]'; then
  printf 'ok    json    parses and reports issues\n'; ((pass++))
else
  printf 'FAIL  json    output is not valid JSON, or reports nothing\n'; ((fail++))
fi

echo
echo "== this plugin's own skills must pass the audit =="
audit="$HERE/../../skill-forge/scripts/audit_skills.py"
if [[ -f "$audit" ]]; then
  own="$("$PY" "$audit" "$HERE/../skills" 2>&1)"
  if [[ $? == "0" ]]; then
    printf 'ok    self    %s\n' "${own##*$'\n'}"; ((pass++))
  else
    printf 'FAIL  self    %s\n' "$own"; ((fail++))
  fi
else
  printf 'ok    self    skipped, skill-forge not present\n'; ((pass++))
fi

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
