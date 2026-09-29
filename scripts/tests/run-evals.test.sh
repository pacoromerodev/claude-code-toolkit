#!/usr/bin/env bash
# Tests for scripts/run-evals.sh, with a stub in place of claude: nothing here
# calls a model or spends money.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$HERE/../run-evals.sh"

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
cd "$SANDBOX" || exit 1

pass=0
fail=0
ok()  { printf 'ok    %s\n' "$1"; pass=$((pass + 1)); return 0; }
bad() { printf 'FAIL  %s\n' "$1"; fail=$((fail + 1)); return 0; }

# A stub claude that records each invocation, one line per call.
stub="$SANDBOX/claude"
# --version answers without being logged, so the counts below stay one line
# per case.
printf '#!/usr/bin/env bash\n[ "$1" = --version ] && { echo "9.9.9 (Claude Code)"; exit 0; }\necho "$*" >> "%s/calls"\n' "$SANDBOX" > "$stub"
chmod +x "$stub"
# Every run names its model; the cases below that test a missing one unset it.
export EVAL_MODEL=claude-test-model
export EVAL_JUDGE_MODEL=claude-test-judge

# Two homes: one whose Docker store holds a symlink, one whose store is plain.
mkdir -p "$SANDBOX/linked/.docker" "$SANDBOX/plain/.docker" "$SANDBOX/elsewhere"
ln -s "$SANDBOX/elsewhere" "$SANDBOX/linked/.docker/contexts"
: > "$SANDBOX/plain/.docker/config.json"

# Count the cases of one plugin, and how many of them need Bash.
plugin=team-rollout  # has cases with and without needs-bash
evals="$HERE/../../plugins/$plugin/evals"
total=$(ls "$evals"/*/case.yaml | wc -l)
needs_bash=$(grep -l '^tags: .*needs-bash' "$evals"/*/case.yaml | wc -l)

echo "== store with a symbolic link =="
rm -f "$SANDBOX/calls"
out="$(HOME="$SANDBOX/linked" DOCKER_CONFIG="" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/out" bash "$RUNNER" "$plugin" 2>&1)"
calls=$(wc -l < "$SANDBOX/calls" 2>/dev/null || echo 0)
[[ "$calls" -eq $((total - needs_bash)) ]] && ok "runs only the cases that do not need Bash ($calls)" \
  || bad "ran $calls case(s), wanted $((total - needs_bash))"
grep -q -- '--allow-tools Bash' "$SANDBOX/calls" && bad "granted Bash" || ok "never grants Bash"
[[ "$out" == *"NOT RUN ($needs_bash case(s)"* ]] && ok "lists the skipped cases as NOT RUN" \
  || bad "does not list the skipped cases: $out"
grep -q -- '--no-publish' "$SANDBOX/calls" && ok "never publishes" || bad "publishes the report"

echo
echo "== plain store =="
rm -f "$SANDBOX/calls"
out="$(HOME="$SANDBOX/plain" DOCKER_CONFIG="" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/out2" bash "$RUNNER" "$plugin" 2>&1)"
calls=$(wc -l < "$SANDBOX/calls" 2>/dev/null || echo 0)
[[ "$calls" -eq "$total" ]] && ok "runs every case ($calls)" || bad "ran $calls case(s), wanted $total"
grep -q -- '--allow-tools Bash Write Edit' "$SANDBOX/calls" && ok "grants Bash, Write and Edit" \
  || bad "does not grant Bash"
[[ "$out" != *"NOT RUN"* ]] && ok "reports nothing skipped" || bad "reported skipped cases"

echo
echo "== results stay outside the repository =="
if grep -q -- "--output-dir $SANDBOX/out2/" "$SANDBOX/calls"; then ok "output dir is the one given"; else bad "output dir not passed"; fi

echo
echo "== --stale runs only what has no current measurement =="
fixture="$SANDBOX/repo"
mkdir -p "$fixture/plugins/demo/evals/fresh-case" "$fixture/plugins/demo/evals/changed-case" "$fixture/.github/scripts"
cp "$HERE/../../.github/scripts/eval_ledger.py" \
   "$HERE/../../.github/scripts/check_eval_freshness.py" "$fixture/.github/scripts/"
for c in fresh-case changed-case; do
  printf 'schema_version: "1.0"\nname: %s\ntags: [demo, skill]\n' "$c" \
    > "$fixture/plugins/demo/evals/$c/case.yaml"
done
python3 - "$fixture" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / ".github/scripts"))
from eval_ledger import case_fingerprint, write_ledger
demo = root / "plugins/demo"
write_ledger(demo, {
    # A real measurement has both arms: a score with no baseline counts as
    # unmeasured (see check_eval_freshness.py), and --stale would re-run it.
    "fresh-case": {"score": 1.0, "baseline": 1.0, "delta": 0.0,
                   "model": "claude-test-model", "judge": "claude-test-judge",
                   "measured": "2026-09-20",
                   "fingerprint": case_fingerprint(demo / "evals/fresh-case")},
    "changed-case": {"score": 1.0, "measured": "2026-09-20",
                     "fingerprint": "0000000000000000"},
})
PY
stale_out="$(EVAL_ROOT="$fixture" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/stale-out" \
  bash "$RUNNER" --stale --dry-run demo 2>&1)"
[[ "$stale_out" == *"--case changed-case"* ]] \
  && ok "--stale runs the case that changed" || bad "--stale skipped the changed case"
[[ "$stale_out" != *"--case fresh-case"* ]] \
  && ok "--stale skips the case already measured" || bad "--stale re-ran a measured case"
[[ "$stale_out" == *"SKIPPED (1 case"* ]] \
  && ok "--stale says how many it skipped" || bad "--stale did not report the skip"
all_out="$(EVAL_ROOT="$fixture" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/all-out" \
  bash "$RUNNER" --dry-run demo 2>&1)"
[[ "$all_out" == *"--case fresh-case"* && "$all_out" == *"--case changed-case"* ]] \
  && ok "without --stale every case runs" || bad "without --stale did not run both"

echo
echo "== the model is named, passed and recorded =="
rm -f "$SANDBOX/calls"
out="$(EVAL_MODEL="" HOME="$SANDBOX/plain" DOCKER_CONFIG="" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/nomodel" \
  bash "$RUNNER" "$plugin" 2>&1)"; code=$?
[[ "$code" -eq 2 && ! -s "$SANDBOX/calls" && "$out" == *"--model"* ]] \
  && ok "refuses to run without a model" || bad "ran with no model named (exit $code)"
HOME="$SANDBOX/plain" DOCKER_CONFIG="" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/withmodel" \
  bash "$RUNNER" --model claude-other-model "$plugin" >/dev/null 2>&1
grep -q -- "--model claude-other-model" "$SANDBOX/calls" \
  && ok "--model reaches the eval" || bad "--model was not passed to the eval"
# The fixture's measured case was measured on claude-test-model: for any other
# model it has no current measurement.
model_out="$(EVAL_ROOT="$fixture" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/model-out" \
  bash "$RUNNER" --model claude-other-model --stale --dry-run demo 2>&1)"
[[ "$model_out" == *"--case fresh-case"* ]] \
  && ok "--stale re-runs a case measured on another model" \
  || bad "--stale kept a case measured on another model"

# The judge is part of the measurement too.
rm -f "$SANDBOX/calls"
HOME="$SANDBOX/plain" DOCKER_CONFIG="" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/judged" \
  bash "$RUNNER" "$plugin" >/dev/null 2>&1
grep -q -- "--judge-model claude-test-judge" "$SANDBOX/calls" \
  && ok "the judge reaches the eval" || bad "--judge-model was not passed"
rm -f "$SANDBOX/calls"
EVAL_JUDGE_MODEL="" HOME="$SANDBOX/plain" DOCKER_CONFIG="" CLAUDE_BIN="$stub" \
  OUT_DIR="$SANDBOX/default-judge" bash "$RUNNER" "$plugin" >/dev/null 2>&1
grep -q -- "--judge-model claude-sonnet-5" "$SANDBOX/calls" \
  && ok "the judge defaults to Sonnet, not the eval's Haiku" \
  || bad "no default judge was passed"
judge_out="$(EVAL_ROOT="$fixture" CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/judge-out" \
  bash "$RUNNER" --judge-model claude-other-judge --stale --dry-run demo 2>&1)"
[[ "$judge_out" == *"--case fresh-case"* ]] \
  && ok "--stale re-runs a case graded by another judge" \
  || bad "--stale kept a case graded by another judge"

# The CLI version that ran the eval is recorded with the number.
pystub="$SANDBOX/python-stub"
printf '#!/usr/bin/env bash\necho "$*" >> "%s/python-calls"\n' "$SANDBOX" > "$pystub"
chmod +x "$pystub"
mkdir -p "$SANDBOX/cli-out/$plugin"
echo '{"cases":[]}' > "$SANDBOX/cli-out/$plugin/some-case.json"
HOME="$SANDBOX/plain" DOCKER_CONFIG="" CLAUDE_BIN="$stub" PYTHON="$pystub" \
  OUT_DIR="$SANDBOX/cli-out" bash "$RUNNER" "$plugin" >/dev/null 2>&1
grep -q -- "record_measurement.py .*--cli 9.9.9" "$SANDBOX/python-calls" \
  && ok "the CLI version reaches the ledger" || bad "--cli was not passed to the recorder"

echo
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
