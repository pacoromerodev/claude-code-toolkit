#!/usr/bin/env bash
# Fixture tests for the caching auditor and the RRF fusion script.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$HERE/../scripts"
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

# `return 0`: ((pass++)) yields the pre-increment value, which would trip the
# `|| bad` branch on the first call.
ok()  { printf 'ok    %-8s %s\n' "$1" "$2"; pass=$((pass + 1)); return 0; }
bad() { printf 'FAIL  %-8s %s\n' "$1" "$2"; fail=$((fail + 1)); return 0; }

bad_output="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/bad_caching.py" 2>&1)"
bad_code=$?
good_output="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/good_caching.py" 2>&1)"
good_code=$?

echo "== caching: planted faults must be found =="
[[ "$bad_output" == *"volatile-prefix"* ]] \
  && ok finds "a timestamp inside a cached prefix" || bad finds "volatile prefix"
[[ "$bad_output" == *"too-many-breakpoints"* ]] \
  && ok finds "more than four breakpoints" || bad finds "too many breakpoints"
[[ "$bad_output" == *"short-prefix"* ]] \
  && ok finds "a cached prefix too short to store" || bad finds "short prefix"
[[ "$bad_output" == *"unverified-caching"* ]] \
  && ok finds "caching with usage never read" || bad finds "unverified caching"

echo
echo "== caching: the message explains the cost =="
[[ "$bad_output" == *"write premium on every request"* ]] \
  && ok says "volatile prefix says it is worse than no caching" \
  || bad says "volatile prefix message is bare"

echo
echo "== caching: the good file must produce nothing =="
if [[ "$good_output" == *"Clean —"* ]]; then
  ok quiet "no findings at all"
else
  bad quiet "reported: $(printf '%s' "$good_output" | head -2 | tr '\n' ' ')"
fi

# A prefix built from a module-level constant has unknown length at parse
# time. Measuring the SOURCE would call an 6000-character prompt too short.
[[ "$good_output" != *"short-prefix"* ]] \
  && ok quiet "a prefix from a constant is not called short" \
  || bad quiet "measured source length instead of value length"

echo
echo "== caching: a breakpoint on the newest turn is the normal pattern =="
growing="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/growing_conversation.py" 2>&1)"
growing_code=$?
[[ "$growing_code" == 0 && "$growing" == *"Clean —"* ]] \
  && ok quiet "a cached newest message raises nothing" \
  || bad quiet "reported: $(printf '%s' "$growing" | head -2 | tr '\n' ' ')"
[[ "$growing" != *"automatic"* ]] \
  && ok quiet "top-level cache_control is not called uncached" \
  || bad quiet "hinted at automatic caching for a request that uses it"

varying="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/varying_tail.py" 2>&1)"
[[ "$varying" == *"volatile-breakpoint"* ]] \
  && ok finds "a timestamp in the block the breakpoint sits on" \
  || bad finds "volatile breakpoint"

echo
echo "== request shapes that fail when they run =="
requests_output="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/bad_requests.py" 2>&1)"
requests_code=$?
for probe in "thinking with temperature:thinking-with-temperature" \
             "a thinking budget under the floor:thinking-budget-too-small" \
             "a budget that leaves no room:thinking-budget-over-max" \
             "effort as its own argument:effort-top-level" \
             "effort inside thinking:effort-in-thinking" \
             "system=None:system-none" \
             "a tool loop with no is_error:tool-errors-unreported"; do
  label="${probe%%:*}"; needle="${probe#*:}"
  [[ "$requests_output" == *"$needle"* ]] && ok finds "$label" || bad finds "$label"
done
[[ "$requests_code" == 1 ]] && ok exit "bad requests exit 1" \
  || bad exit "wanted 1, got $requests_code"

good_requests="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/good_requests.py" 2>&1)"
good_requests_code=$?
[[ "$good_requests_code" == 0 && "$good_requests" == *"Clean —"* ]] \
  && ok quiet "the correct shapes report nothing" \
  || bad quiet "reported: $(printf '%s' "$good_requests" | head -2 | tr '\n' ' ')"

echo
echo "== caching: exit codes =="
[[ "$bad_code" == 1 ]] && ok exit "errors present (1)" || bad exit "wanted 1, got $bad_code"
[[ "$good_code" == 0 ]] && ok exit "nothing wrong (0)" || bad exit "wanted 0, got $good_code"

echo
echo "== caching: json output =="
json="$("$PY" "$SCRIPTS/check_api_calls.py" "$FIXTURES/bad_caching.py" --json 2>/dev/null)"
if printf '%s' "$json" | "$PY" -c \
   'import json,sys; d=json.load(sys.stdin); assert d["errors"]>0 and d["calls"]>0'; then
  ok json "parses and reports findings"
else
  bad json "not valid JSON, or reports nothing"
fi

echo
echo "== RRF fusion =="
fuse_json="$("$PY" "$SCRIPTS/fuse.py" "$FIXTURES/rankings.json" --json 2>&1)"
fuse_code=$?
[[ "$fuse_code" == 0 ]] && ok exit "fuse exits 0" || bad exit "fuse exited $fuse_code"

# s2 is semantic#1 and bm25#2; s7 is bm25#1 and semantic#3. Agreement near the
# top must beat a single first place — that is the property RRF is chosen for.
if printf '%s' "$fuse_json" | "$PY" -c '
import json, sys
rows = json.load(sys.stdin)
ids = [r["id"] for r in rows]
assert ids[0] == "s2", f"expected s2 first, got {ids[0]}"
assert ids[1] == "s7", f"expected s7 second, got {ids[1]}"
assert rows[0]["score"] > rows[1]["score"]
'; then
  ok rrf "agreement outranks a single first place"
else
  bad rrf "ranking is wrong: $(printf '%s' "$fuse_json" | head -3 | tr '\n' ' ')"
fi

# Documents found by both retrievers must carry both ranks.
if printf '%s' "$fuse_json" | "$PY" -c '
import json, sys
rows = {r["id"]: r for r in json.load(sys.stdin)}
assert set(rows["s2"]["ranks"]) == {"semantic", "bm25"}
assert rows["s2"]["ranks"]["semantic"] == 1
assert rows["s6"]["ranks"] == {"semantic": 2}
'; then
  ok rrf "reports which retriever found each document, and where"
else
  bad rrf "rank provenance is wrong"
fi

echo
echo "== RRF edge cases =="
if "$PY" -c '
import sys
sys.path.insert(0, "'"$SCRIPTS"'")
from fuse import fuse

# A repeat inside one ranking must not score twice.
once = fuse({"a": ["x"]})
twice = fuse({"a": ["x", "x"]})
assert once[0][1] == twice[0][1], "a duplicate scored twice"

# A single ranking passes straight through, order intact.
assert [d for d, _, _ in fuse({"a": ["p", "q", "r"]})] == ["p", "q", "r"]

# Ties break deterministically on the id.
first = [d for d, _, _ in fuse({"a": ["b", "a"], "z": ["a", "b"]})]
second = [d for d, _, _ in fuse({"z": ["a", "b"], "a": ["b", "a"]})]
assert first == second, "fusion is not deterministic"

# k must be positive.
try:
    fuse({"a": ["x"]}, k=0)
    raise AssertionError("k=0 was accepted")
except ValueError:
    pass

# limit truncates.
assert len(fuse({"a": ["1", "2", "3", "4"]}, limit=2)) == 2
' 2>&1; then
  ok rrf "duplicates, single lists, ties, k=0 and limit all behave"
else
  bad rrf "an edge case failed"
fi

echo
echo "== this plugin's own skills must pass the audit =="
audit="$HERE/../../skill-forge/scripts/audit_skills.py"
if [[ -f "$audit" ]]; then
  own="$("$PY" "$audit" "$HERE/../skills" 2>&1)"
  if [[ $? == 0 ]]; then ok self "${own##*$'\n'}"; else bad self "$own"; fi
else
  ok self "skipped, skill-forge not present"
fi

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
