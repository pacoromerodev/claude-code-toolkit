#!/usr/bin/env bash
# Fixture tests for the skills auditor.
#
# fixtures/broken/ has one planted fault per directory; fixtures/clean/ has a
# skill that should pass untouched. Every fault must be found, and the clean
# tree must stay quiet — a linter with false positives gets ignored, which is
# the same as not having one.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT="$HERE/../scripts/audit_skills.py"
FIXTURES="$HERE/fixtures"
PY="${PYTHON:-python3}"

pass=0
fail=0

broken_output="$("$PY" "$AUDIT" "$FIXTURES/broken" 2>&1)"
broken_code=$?
clean_output="$("$PY" "$AUDIT" "$FIXTURES/clean" 2>&1)"
clean_code=$?

# finds <description> <substring>
finds() {
  if [[ "$broken_output" == *"$2"* ]]; then
    printf 'ok    finds   %s\n' "$1"
    ((pass++))
  else
    printf 'FAIL  finds   %s — nothing matched %q\n' "$1" "$2"
    ((fail++))
  fi
}

# quiet <description> <substring>  — must NOT appear for the clean tree
quiet() {
  if [[ "$clean_output" != *"$2"* ]]; then
    printf 'ok    quiet   %s\n' "$1"
    ((pass++))
  else
    printf 'FAIL  quiet   %s — clean tree reported %q\n' "$1" "$2"
    ((fail++))
  fi
}

# code <description> <actual> <expected>
code() {
  if [[ "$2" == "$3" ]]; then
    printf 'ok    exit    %s (%s)\n' "$1" "$2"
    ((pass++))
  else
    printf 'FAIL  exit    %s — got %s, wanted %s\n' "$1" "$2" "$3"
    ((fail++))
  fi
}

echo "== planted faults must all be found =="
finds "name not matching its directory"  "but the directory is"
finds "missing SKILL.md"                 "has no SKILL.md"
finds "missing frontmatter"              "no YAML frontmatter"
finds "body over the line limit"         "over the 500 limit"
finds "description with no trigger"      "never says when to use"
finds "description opening with 'this skill'" 'opens with "this skill"'
finds "unreferenced reference file"      "never mentioned in SKILL.md"
finds "overlapping descriptions"         "overlaps"

echo
echo "== the clean tree must stay quiet =="
quiet "no errors"        "ERROR"
quiet "no warnings"      "warn "
finds_clean=$([[ "$clean_output" == *"Clean —"* ]] && echo yes || echo no)
if [[ "$finds_clean" == "yes" ]]; then
  printf 'ok    quiet   reports clean\n'; ((pass++))
else
  printf 'FAIL  quiet   did not report clean: %s\n' "${clean_output%%$'\n'*}"; ((fail++))
fi

echo
echo "== exit codes =="
code "errors present" "$broken_code" 1
code "nothing wrong"  "$clean_code"  0

echo
echo "== json output is parseable =="
# Captured first, not piped: the auditor exits 1 when it finds errors, and
# under `set -o pipefail` that legitimate exit would fail the pipeline.
json_output="$("$PY" "$AUDIT" "$FIXTURES/broken" --json 2>/dev/null)"
if printf '%s' "$json_output" | "$PY" -c \
   'import json,sys; d=json.load(sys.stdin); assert d["errors"]>0 and d["findings"]'; then
  printf 'ok    json    parses and reports findings\n'; ((pass++))
else
  printf 'FAIL  json    output is not valid JSON, or reports nothing\n'; ((fail++))
fi

echo
echo "== this repo's own skills must be clean =="
own="$("$PY" "$AUDIT" "$HERE/../../"*/skills 2>&1)"
own_code=$?
if [[ "$own_code" == "0" ]]; then
  printf 'ok    self    %s\n' "${own##*$'\n'}"
  ((pass++))
else
  printf 'FAIL  self    the toolkit fails its own audit:\n%s\n' "$own"
  ((fail++))
fi

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
