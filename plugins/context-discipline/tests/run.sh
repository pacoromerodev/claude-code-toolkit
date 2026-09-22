#!/usr/bin/env bash
# Fixture tests for context-discipline.
#
# Two halves: the CLAUDE.md auditor against a bad file and a good one, and the
# save → restore cycle exercised end to end in a throwaway git repo.
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

# The explicit `return 0` matters: `((pass++))` evaluates to the value BEFORE
# the increment, so the first call would return 1 and trip the `|| bad` branch
# of every `[[ ... ]] && ok || bad` below.
ok()   { printf 'ok    %-8s %s\n' "$1" "$2"; pass=$((pass + 1)); return 0; }
bad()  { printf 'FAIL  %-8s %s\n' "$1" "$2"; fail=$((fail + 1)); return 0; }

bad_output="$("$PY" "$SCRIPTS/check_claude_md.py" "$FIXTURES/bad-CLAUDE.md" 2>&1)"
bad_code=$?
good_output="$("$PY" "$SCRIPTS/check_claude_md.py" "$FIXTURES/good-CLAUDE.md" 2>&1)"
good_code=$?

echo "== the bad CLAUDE.md: every planted fault must be found =="
for probe in "vague:a standard without naming one" \
             "emphasis:emphasis markers" \
             "no-alternative:prohibition with no alternative" \
             "broken-import:does not exist" \
             "prose-block:very long paragraph"; do
  label="${probe%%:*}"; needle="${probe#*:}"
  [[ "$bad_output" == *"$needle"* ]] && ok finds "$label" || bad finds "$label"
done

echo
echo "== the good CLAUDE.md must produce nothing =="
if [[ "$good_output" == *"Clean —"* ]]; then
  ok quiet "no findings at all"
else
  bad quiet "reported: $(printf '%s' "$good_output" | head -2 | tr '\n' ' ')"
fi

echo
echo "== exit codes =="
[[ "$bad_code" == 1 ]] && ok exit "error present (1)" || bad exit "wanted 1, got $bad_code"
[[ "$good_code" == 0 ]] && ok exit "nothing wrong (0)" || bad exit "wanted 0, got $good_code"

echo
echo "== json output =="
json="$("$PY" "$SCRIPTS/check_claude_md.py" "$FIXTURES/bad-CLAUDE.md" --json 2>/dev/null)"
if printf '%s' "$json" | "$PY" -c \
   'import json,sys; d=json.load(sys.stdin); assert d["errors"]>0 and d["findings"]'; then
  ok json "parses and reports findings"
else
  bad json "not valid JSON, or reports nothing"
fi

echo
echo "== save → restore, end to end =="
work="$(mktemp -d)"
trap 'rm -rf "$work" "$SANDBOX"' EXIT
(
  cd "$work" || exit 1
  git init -q -b main . && git config user.email t@example.invalid && \
    git config user.name Test
  echo "first" > app.txt && git add -A && git commit -qm "Add app"
  echo "changed" > app.txt && echo "new" > extra.txt
) >/dev/null 2>&1

payload='{"session_id":"sess-abc","cwd":"'"$work"'","trigger":"auto"}'

printf '%s' "$payload" | "$PY" "$SCRIPTS/save_state.py" >/dev/null 2>&1
save_code=$?
[[ "$save_code" == 0 ]] && ok exit "save exits 0 ($save_code)" || bad exit "save exited $save_code"

snapshot="$work/.claude/state/sess-abc.md"
if [[ -f "$snapshot" ]]; then
  ok save "snapshot written, namespaced by session id"
else
  bad save "no snapshot at .claude/state/sess-abc.md"
fi

snap="$(cat "$snapshot" 2>/dev/null)"
[[ "$snap" == *"main"* ]]      && ok save "records the branch"          || bad save "branch missing"
[[ "$snap" == *"extra.txt"* ]] && ok save "records untracked files"     || bad save "untracked file missing"
[[ "$snap" == *"Add app"* ]]   && ok save "records recent commits"      || bad save "commits missing"

restore_out="$(printf '%s' "$payload" | "$PY" "$SCRIPTS/restore_state.py" 2>&1)"
if printf '%s' "$restore_out" | "$PY" -c '
import json,sys
d = json.load(sys.stdin)
ctx = d["hookSpecificOutput"]["additionalContext"]
assert "extra.txt" in ctx, "snapshot body missing"
assert "Verify anything you act on" in ctx, "no caveat about staleness"
'; then
  ok restore "emits additionalContext carrying the snapshot"
else
  bad restore "output: $(printf '%s' "$restore_out" | head -1)"
fi

# A handoff note is written on purpose and must outrank measured facts.
mkdir -p "$work/.claude"
printf 'Goal: finish the parser.\nNext: handle escaped quotes.\n' > "$work/.claude/handoff.md"
printf '%s' "$payload" | "$PY" "$SCRIPTS/save_state.py" >/dev/null 2>&1
if grep -q "escaped quotes" "$snapshot" 2>/dev/null; then
  ok save "includes the handoff note"
else
  bad save "handoff note not picked up"
fi

echo
echo "== hooks must fail open =="
for script in save_state.py restore_state.py; do
  printf 'not json' | "$PY" "$SCRIPTS/$script" >/dev/null 2>&1
  [[ $? == 0 ]] && ok open "$script survives a malformed payload" \
                || bad open "$script exited non-zero on bad input"
done

# No snapshot at all must be silent, not an empty JSON object.
empty="$(mktemp -d)"
out="$(printf '{"session_id":"x","cwd":"%s"}' "$empty" | "$PY" "$SCRIPTS/restore_state.py" 2>&1)"
[[ -z "$out" ]] && ok open "restore is silent with no snapshot" \
                || bad open "restore printed something with no snapshot: $out"
rm -rf "$empty"

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
