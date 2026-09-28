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

# A workflow that runs Claude unattended: every M4 finding must appear.
out="$("$PY" "$SCRIPTS/check_workflows.py" "$FIXTURES/workflows/unattended" 2>&1)"
expect_exit "workflows unattended" "$?" 1
expect_text "workflows unattended" "$out" "runs Claude with no --max-turns"
expect_text "workflows unattended" "$out" "runs Claude with permissions bypassed"
expect_text "workflows unattended" "$out" "grants Bash, Write, Edit with no pattern"
expect_text "workflows unattended" "$out" "actions/checkout is used at @main"
expect_text "workflows unattended" "$out" "\${{ }} inside a run: block"
# `plugin eval` is bounded by its own case files, so its operator grant and
# its lack of --max-turns are not findings.
if ! printf '%s\n' "$out" | grep -q "evals.yml.*no --max-turns"; then
  ok "workflows unattended" "leaves plugin eval's own bounds alone"
else
  bad "workflows unattended" "asked plugin eval for --max-turns"
fi

echo
echo "== check_course_wording.py =="
# Fingerprints built from a fixture note, never from the real ones: this
# repository holds no course text, hashed or otherwise, beyond data/.
fp="$SANDBOX/fingerprints.txt"
"$PY" "$SCRIPTS/check_course_wording.py" --update \
  --notes "$FIXTURES/course-wording/notes" --fingerprints "$fp" > /dev/null
out="$("$PY" "$SCRIPTS/check_course_wording.py" --enforce --fingerprints "$fp" \
  "$FIXTURES/course-wording/good" 2>&1)"
expect_exit "wording good" "$?" 0
out="$("$PY" "$SCRIPTS/check_course_wording.py" --enforce --fingerprints "$fp" \
  "$FIXTURES/course-wording/bad" 2>&1)"
expect_exit "wording bad" "$?" 1
expect_text "wording bad" "$out" "ledger entry for the auditor"
# --notes repeats, and a lesson one directory down is read: the English
# originals live in per-course folders, and missing them is missing the source.
fp2="$SANDBOX/fingerprints-both.txt"
"$PY" "$SCRIPTS/check_course_wording.py" --update \
  --notes "$FIXTURES/course-wording/notes" \
  --notes "$FIXTURES/course-wording/lessons" --fingerprints "$fp2" > /dev/null
out="$("$PY" "$SCRIPTS/check_course_wording.py" --enforce --fingerprints "$fp2" \
  "$FIXTURES/course-wording/bad-lesson" 2>&1)"
expect_exit "wording from a nested lesson" "$?" 1
expect_text "wording from a nested lesson" "$out" "the purchase order it cites"
out="$("$PY" "$SCRIPTS/check_course_wording.py" --enforce --fingerprints "$fp2" \
  "$FIXTURES/course-wording/bad" 2>&1)"
expect_exit "wording from the first --notes still read" "$?" 1
out="$("$PY" "$SCRIPTS/check_course_wording.py" --enforce --fingerprints "$fp" \
  "$FIXTURES/course-wording/bad-lesson" 2>&1)"
expect_exit "wording lesson unseen without its --notes" "$?" 0
out="$("$PY" "$SCRIPTS/check_course_wording.py" --fingerprints "$fp" \
  "$FIXTURES/course-wording/bad" 2>&1)"
expect_exit "wording bad, report-only" "$?" 0

echo
echo "== check_eval_freshness.py =="
out="$("$PY" "$SCRIPTS/check_eval_freshness.py" "$FIXTURES/freshness" 2>&1)"
expect_exit "freshness report-only" "$?" 0
expect_text "freshness" "$out" "ok     demo/measured-case"
expect_text "freshness" "$out" "STALE  demo/edited-case"
expect_text "freshness" "$out" "never  demo/new-case"
# A score whose baseline arm all errored is not a delta, and must not read as
# measured: --stale would then never run it again.
expect_text "freshness" "$out" "NOBAS  demo/half-measured-case"
expect_text "freshness" "$out" "1 measured, 1 changed since, 1 without a baseline, 1 never run"
out="$("$PY" "$SCRIPTS/check_eval_freshness.py" --list-stale "$FIXTURES/freshness" 2>&1)"
expect_text "freshness --list-stale" "$out" "demo/half-measured-case"
out="$("$PY" "$SCRIPTS/check_eval_freshness.py" --enforce "$FIXTURES/freshness" 2>&1)"
expect_exit "freshness --enforce" "$?" 1
# Measured on a model the ledger does not name: stale for any named model.
out="$("$PY" "$SCRIPTS/check_eval_freshness.py" --model claude-test-model "$FIXTURES/freshness" 2>&1)"
expect_text "freshness --model" "$out" "STALE  demo/measured-case"
expect_text "freshness --model" "$out" "measured on an unrecorded model"
out="$("$PY" "$SCRIPTS/check_eval_freshness.py" --judge claude-test-judge "$FIXTURES/freshness" 2>&1)"
expect_text "freshness --judge" "$out" "judged by an unrecorded judge"

echo
echo "== record_measurement.py =="
# A run whose every arm errored is not a measurement, and must not be written
# down as one: those runs score 0.00 in the file, exactly like a plugin that
# failed. Three attempts at this suite were misread that way.
ledger_dir="$SANDBOX/ledger/demo"
mkdir -p "$ledger_dir/evals/some-case"
printf 'schema_version: "1.0"\nname: some-case\n' > "$ledger_dir/evals/some-case/case.yaml"
cat > "$SANDBOX/good-result.json" <<'JSON'
{"cases":[{"name":"some-case","arms":{"with":[{"score":1},{"score":1},{"score":0}],
 "without":[{"score":0},{"score":0},{"score":0}]}}]}
JSON
cat > "$SANDBOX/failed-result.json" <<'JSON'
{"cases":[{"name":"some-case","arms":{"with":[{"score":0,"error":"exit 1: Credit balance is too low"}],
 "without":[{"score":0,"error":"exit 1: Credit balance is too low"}]}}]}
JSON
out="$("$PY" "$SCRIPTS/record_measurement.py" "$ledger_dir" "$SANDBOX/good-result.json" 2>&1)"
expect_exit "record a real run" "$?" 0
expect_text "record a real run" "$out" "Recorded 1 case(s)"
recorded="$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1]))["cases"]["some-case"]; print(d["score"], d["baseline"], d["runs"])' "$ledger_dir/evals/measurements.json")"
[[ "$recorded" == "0.67 0.0 3" ]] \
  && ok "record a real run" "mean of the runs that happened" \
  || bad "record a real run" "recorded $recorded"
out="$("$PY" "$SCRIPTS/record_measurement.py" "$ledger_dir" "$SANDBOX/failed-result.json" 2>&1)"
expect_text "record a failed run" "$out" "Not recorded, because every run errored"
still="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["cases"]["some-case"]["score"])' "$ledger_dir/evals/measurements.json")"
[[ "$still" == "0.67" ]] \
  && ok "record a failed run" "leaves the previous measurement alone" \
  || bad "record a failed run" "overwrote it with $still"
# The result file does not say which model ran; the recorder writes what it is
# told, so a number can later be compared only against its own model.
"$PY" "$SCRIPTS/record_measurement.py" --model claude-test-model "$ledger_dir" \
  "$SANDBOX/good-result.json" >/dev/null 2>&1
model="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["cases"]["some-case"].get("model"))' "$ledger_dir/evals/measurements.json")"
[[ "$model" == "claude-test-model" ]] \
  && ok "record --model" "writes the model beside the number" \
  || bad "record --model" "recorded model $model"
"$PY" "$SCRIPTS/record_measurement.py" --model claude-test-model --judge claude-test-judge \
  "$ledger_dir" "$SANDBOX/good-result.json" >/dev/null 2>&1
judge="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["cases"]["some-case"].get("judge"))' "$ledger_dir/evals/measurements.json")"
[[ "$judge" == "claude-test-judge" ]] \
  && ok "record --judge" "writes the judge beside the number" \
  || bad "record --judge" "recorded judge $judge"

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
