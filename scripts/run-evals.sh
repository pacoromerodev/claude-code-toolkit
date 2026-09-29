#!/usr/bin/env bash
# Run the plugins' eval suites locally, and say plainly what did not run.
#
#   scripts/run-evals.sh --model <id> [--judge-model <id>] [--runs N] [--stale]
#                        [--dry-run] [plugin ...]
#
# Evaluates the working copy (plugins/<name>), not the installed plugin. Every
# result goes to a directory outside the repository, and nothing is published.
#
# `claude plugin eval` refuses any run that grants Bash when the Docker
# credential store (DOCKER_CONFIG, or ~/.docker) holds a symbolic link, because
# its sandbox cannot then reliably keep the store out of reach. This script
# never touches the store. When the condition holds it grants only Write and
# Edit, skips every case tagged `needs-bash`, and lists those cases as NOT RUN
# at the end, so a partial run is never mistaken for a full one.
#
# --model is required (or EVAL_MODEL): pass a full model id, not an alias.
# `claude plugin eval` otherwise uses the user's default, which is usually an
# alias like `opus` that points at a new model after an update, and its
# result file does not say which model ran. The id is passed to the eval and
# written into the ledger with each number.
#
# --judge-model names the model that grades the answers, claude-sonnet-5-5
# unless given. The eval's own default is Haiku, which on 2026-09-26 failed,
# three votes in three, an answer that met every line of its criteria. The
# judge is recorded with the model, and --stale re-runs anything judged by
# another.
#
# Environment:
#   EVAL_MODEL   the model id, when --model is not given
#   EVAL_JUDGE_MODEL  the judge's id, when --judge-model is not given
#   CLAUDE_BIN   the claude executable (default: claude); tests use a stub
#   EVAL_ROOT    the repository to evaluate (default: this one)
#   OUT_DIR      where results go (default: a new temporary directory)
#   PYTHON       the interpreter that records the measurements
#
# After each plugin, what it measured is written into
# plugins/<plugin>/evals/measurements.json, so that a case edited later shows
# up as unmeasured rather than keeping an old number.
#
# --stale runs only the cases that ledger says have no current measurement:
# edited since they were last run, or never run at all. A full pass costs
# real money, so re-measuring what changed is what makes it a habit rather
# than an event.
set -uo pipefail

# EVAL_ROOT exists so the tests can point this at a fixture tree; in normal
# use it is the repository this script lives in.
ROOT="${EVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
RUNS=""
MODEL="${EVAL_MODEL:-}"
JUDGE="${EVAL_JUDGE_MODEL:-claude-sonnet-5-5}"
DRY_RUN=0
STALE_ONLY=0
PLUGINS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runs) RUNS="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --judge-model) JUDGE="$2"; shift 2 ;;
    --stale) STALE_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) PLUGINS+=("$1"); shift ;;
  esac
done

if [[ -z "$MODEL" ]]; then
  echo "run-evals.sh: name the model with --model <id> (or EVAL_MODEL)." >&2
  echo "A measurement without its model cannot be compared with the next one." >&2
  exit 2
fi

# The CLI is part of the measurement: the same case scored differently across
# versions before, and the result file does not say which one ran.
CLI_VERSION="$("$CLAUDE_BIN" --version 2>/dev/null | awk 'NR==1{print $1}')"
record_cli=()
[[ -n "$CLI_VERSION" ]] && record_cli=(--cli "$CLI_VERSION")

if [[ ${#PLUGINS[@]} -eq 0 ]]; then
  for dir in "$ROOT"/plugins/*/; do PLUGINS+=("$(basename "$dir")"); done
fi

# Does the Docker credential store hold a symbolic link below its root?
store="${DOCKER_CONFIG:-$HOME/.docker}"
bash_blocked=0
if [[ -d "$store" ]] && [[ -n "$(find "$store/" -mindepth 1 -type l -print -quit 2>/dev/null)" ]]; then
  bash_blocked=1
fi

if [[ "$bash_blocked" -eq 1 ]]; then
  tools=(Write Edit)
  echo "Docker credential store at $store holds a symbolic link:"
  echo "cases tagged needs-bash will be skipped and listed as NOT RUN."
else
  tools=(Bash Write Edit)
fi

# tags_of <case.yaml>  — the comma-separated tag list, spaces removed
tags_of() { sed -n 's/^tags: *\[\(.*\)\] *$/\1/p' "$1" | tr -d ' '; }

stale_list=""
if [[ "$STALE_ONLY" -eq 1 ]]; then
  stale_list="$("${PYTHON:-python3}" "$ROOT/.github/scripts/check_eval_freshness.py" \
    --list-stale --model "$MODEL" --judge "$JUDGE" "$ROOT" 2>/dev/null)"
  echo "Only cases with no current measurement: $(printf '%s' "$stale_list" | grep -c . ) of $(find "$ROOT"/plugins/*/evals -name case.yaml | wc -l | tr -d ' ')"
fi

# current <plugin/case>  — true when --stale is on and this one is measured
current() {
  [[ "$STALE_ONLY" -eq 1 ]] || return 1
  ! printf '%s\n' "$stale_list" | grep -qx "$1"
}

not_run=()
current_count=0
failed=0
for plugin in "${PLUGINS[@]}"; do
  plugin_dir="$ROOT/plugins/$plugin"
  if [[ ! -d "$plugin_dir/evals" ]]; then
    echo "skip $plugin: no evals/ directory"
    continue
  fi
  for case_file in "$plugin_dir"/evals/*/case.yaml; do
    [[ -f "$case_file" ]] || continue
    name="$(basename "$(dirname "$case_file")")"
    if current "$plugin/$name"; then
      current_count=$((current_count + 1))
      continue
    fi
    if [[ "$bash_blocked" -eq 1 && ",$(tags_of "$case_file")," == *",needs-bash,"* ]]; then
      not_run+=("$plugin/$name")
      continue
    fi
    args=(plugin eval "$plugin_dir" --case "$name" --scaffold --trust-plugin
          --no-publish --model "$MODEL" --judge-model "$JUDGE"
          --allow-tools "${tools[@]}"
          --output-dir "$OUT_DIR/$plugin/$name"
          --json "$OUT_DIR/$plugin/$name.json"
          --report "$OUT_DIR/$plugin/$name.html")
    [[ -n "$RUNS" ]] && args+=(--runs "$RUNS")
    mkdir -p "$OUT_DIR/$plugin"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "would run: $CLAUDE_BIN ${args[*]}"
      continue
    fi
    echo "== $plugin/$name"
    "$CLAUDE_BIN" "${args[@]}" < /dev/null || failed=1
  done

  # Write what this run measured next to the cases. A run whose arms all
  # errored is not recorded: see record_measurement.py.
  if [[ "$DRY_RUN" -eq 0 ]]; then
    shopt -s nullglob
    results=("$OUT_DIR/$plugin"/*.json)
    shopt -u nullglob
    if [[ ${#results[@]} -gt 0 ]]; then
      "${PYTHON:-python3}" "$ROOT/.github/scripts/record_measurement.py" \
        --model "$MODEL" --judge "$JUDGE" ${record_cli[@]+"${record_cli[@]}"} \
        "$plugin_dir" "${results[@]}" || true
    fi
  fi
done

echo
echo "Results: $OUT_DIR"
if [[ "$current_count" -gt 0 ]]; then
  echo "SKIPPED ($current_count case(s) already measured against this exact case)"
fi
if [[ ${#not_run[@]} -gt 0 ]]; then
  echo "NOT RUN (${#not_run[@]} case(s) need Bash, which this machine cannot grant):"
  printf '  %s\n' "${not_run[@]}"
fi
exit "$failed"
