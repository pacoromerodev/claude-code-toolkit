#!/usr/bin/env bash
# Run the plugins' eval suites locally, and say plainly what did not run.
#
#   scripts/run-evals.sh [--runs N] [--dry-run] [plugin ...]
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
# Environment:
#   CLAUDE_BIN   the claude executable (default: claude); tests use a stub
#   OUT_DIR      where results go (default: a new temporary directory)
#   PYTHON       the interpreter that records the measurements
#
# After each plugin, what it measured is written into
# plugins/<plugin>/evals/measurements.json, so that a case edited later shows
# up as unmeasured rather than keeping an old number.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
RUNS=""
DRY_RUN=0
PLUGINS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runs) RUNS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) PLUGINS+=("$1"); shift ;;
  esac
done

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

not_run=()
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
    if [[ "$bash_blocked" -eq 1 && ",$(tags_of "$case_file")," == *",needs-bash,"* ]]; then
      not_run+=("$plugin/$name")
      continue
    fi
    args=(plugin eval "$plugin_dir" --case "$name" --scaffold --trust-plugin
          --no-publish --allow-tools "${tools[@]}"
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
        "$plugin_dir" "${results[@]}" || true
    fi
  fi
done

echo
echo "Results: $OUT_DIR"
if [[ ${#not_run[@]} -gt 0 ]]; then
  echo "NOT RUN (${#not_run[@]} case(s) need Bash, which this machine cannot grant):"
  printf '  %s\n' "${not_run[@]}"
fi
exit "$failed"
