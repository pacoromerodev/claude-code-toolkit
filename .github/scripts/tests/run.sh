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
echo "== check_consistency.py =="
out="$("$PY" "$SCRIPTS/check_consistency.py" "$FIXTURES/consistency/good" 2>&1)"
expect_exit "consistency good" "$?" 0
out="$("$PY" "$SCRIPTS/check_consistency.py" "$FIXTURES/consistency/bad" 2>&1)"
expect_exit "consistency bad" "$?" 1
expect_text "consistency bad" "$out" "plugins/halfway: no .claude-plugin/plugin.json"
# plugins/notes holds nothing plugin-shaped, so it is scratch, not a mistake.
if [[ "$out" != *"plugins/notes"* ]]; then
  ok "consistency bad" "leaves a non-plugin directory alone"
else
  bad "consistency bad" "reports plugins/notes, which is not a plugin"
fi

echo
echo "== check_names.py =="
out="$("$PY" "$SCRIPTS/check_names.py" "$FIXTURES/names/good" 2>&1)"
expect_exit "names good" "$?" 0
out="$("$PY" "$SCRIPTS/check_names.py" "$FIXTURES/names/bad" 2>&1)"
expect_exit "names bad" "$?" 1
expect_text "names bad" "$out" "alpha:audit-widgets: a command and a skill share this name"
expect_text "names bad" "$out" "alpha:widget-review: a command and an agent share this name"
expect_text "names bad" "$out" "beta:verify: Claude Code already ships a command"
expect_text "names bad" "$out" "audit-widgets: used by alpha and beta"

echo
echo "== check_eval_coverage.py =="
out="$("$PY" "$SCRIPTS/check_eval_coverage.py" --enforce "$FIXTURES/eval-coverage/good" 2>&1)"
expect_exit "coverage good" "$?" 0
expect_text "coverage good" "$out" "every skill has two positive cases"
out="$("$PY" "$SCRIPTS/check_eval_coverage.py" "$FIXTURES/eval-coverage/bad" 2>&1)"
expect_exit "coverage bad, report-only" "$?" 0
out="$("$PY" "$SCRIPTS/check_eval_coverage.py" --enforce "$FIXTURES/eval-coverage/bad" 2>&1)"
expect_exit "coverage bad, --enforce" "$?" 1
expect_text "coverage bad" "$out" "demo:widget-check has 1 of 2"
expect_text "coverage bad" "$out" "demo:widget-reviewer has 0 of 1"
expect_text "coverage bad" "$out" "demo has no negative case"
expect_text "coverage bad" "$out" "is tagged 'widgit-check'"

echo
echo "== check_stdlib_only.py =="
out="$("$PY" "$SCRIPTS/check_stdlib_only.py" "$FIXTURES/stdlib/good" 2>&1)"
expect_exit "stdlib good" "$?" 0
out="$("$PY" "$SCRIPTS/check_stdlib_only.py" "$FIXTURES/stdlib/bad" 2>&1)"
expect_exit "stdlib bad" "$?" 1
expect_text "stdlib bad" "$out" "imports 'tomllib', which arrived in Python 3.11"
expect_text "stdlib bad" "$out" "imports 'requests', which is not in the allowed"
expect_text "stdlib bad" "$out" "the matrix starts at 3.12, this script's floor is 3.8"

echo
echo "== check_workflows.py =="
out="$("$PY" "$SCRIPTS/check_workflows.py" "$FIXTURES/workflows/good" 2>&1)"
expect_exit "workflows good" "$?" 0
out="$("$PY" "$SCRIPTS/check_workflows.py" "$FIXTURES/workflows/bad" 2>&1)"
expect_exit "workflows bad" "$?" 1
expect_text "workflows bad" "$out" "no permissions: block"
expect_text "workflows bad" "$out" "checkout without persist-credentials: false"
expect_text "workflows bad" "$out" "inside a run: block"
expect_text "workflows bad" "$out" "@acme/tool is installed unpinned"

echo
echo "== check_hooks.py =="
out="$("$PY" "$SCRIPTS/check_hooks.py" "$FIXTURES/hooks/good" 2>&1)"
expect_exit "hooks good" "$?" 0
out="$("$PY" "$SCRIPTS/check_hooks.py" "$FIXTURES/hooks/bad" 2>&1)"
expect_exit "hooks bad" "$?" 1
expect_text "hooks bad" "$out" "relative path in 'python3 ./scripts/guard.py'"
expect_text "hooks bad" "$out" "scripts/renamed.py does not exist in the plugin"
expect_text "hooks bad" "$out" "Stop[0]: no timeout"
expect_text "hooks bad" "$out" "'PreCommit' is not a hook event"
expect_text "hooks bad" "$out" "SessionStart[0]: uses \$CLAUDE_PROJECT_DIR"

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
