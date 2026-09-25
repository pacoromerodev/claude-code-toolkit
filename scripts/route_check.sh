#!/usr/bin/env bash
# With every plugin installed at once, does each prompt reach the component it
# belongs to?
#
#   scripts/route_check.sh [--list] [name ...]
#
# `claude plugin eval` loads one plugin per run, so it cannot see a collision
# between two of them: two descriptions that both match a prompt each score
# perfectly on their own. This runs the prompts against a session holding all
# seven, reads which Skill or Agent the model actually invoked, and compares it
# with the component the prompt was written for.
#
# Each prompt costs a short session. Run it after changing a description, and
# before a release — not in CI.
#
# Environment:
#   CLAUDE_BIN   the claude executable (default: claude); tests use a stub
#   OUT_DIR      where transcripts go (default: a new temporary directory)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
CASES="$ROOT/scripts/route-cases.tsv"

LIST_ONLY=0
WANTED=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --list) LIST_ONLY=1; shift ;;
    -h|--help) sed -n '2,18p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) WANTED+=("$1"); shift ;;
  esac
done

if [[ ! -f "$CASES" ]]; then
  echo "No route cases at $CASES" >&2
  exit 1
fi

# The transcript names an invoked skill in a tool_use block (Skill, with the
# skill in its input) or a subagent in an Agent (formerly Task) block. This pulls whichever
# appeared first, which is the routing decision; anything after it follows from
# that choice.
invoked_component() {
  "${PYTHON:-python3}" - "$1" <<'PY'
import json
import sys

names = []
with open(sys.argv[1], encoding="utf-8") as stream:
    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        # `content` is a list of blocks on a tool-using turn and a plain
        # string on a text-only one. The string form carries no tool call.
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            payload = block.get("input") or {}
            if block.get("name") == "Skill":
                value = payload.get("skill") or payload.get("command") or ""
                if value:
                    names.append(str(value))
            # The subagent tool is Agent in current Claude Code, Task before.
            elif block.get("name") in ("Agent", "Task"):
                value = payload.get("subagent_type") or ""
                if value:
                    names.append(str(value))

print(names[0] if names else "")
PY
}

# `expected` may list alternatives separated by |: a subagent and the command
# whose only job is to launch it are both correct routes to the same work.
matches() {
  local actual="$1" wanted="$2" option
  while [[ "$wanted" == *"|"* ]]; do
    option="${wanted%%|*}"
    wanted="${wanted#*|}"
    [[ "$actual" == *"$option"* ]] && return 0
  done
  [[ "$actual" == *"$wanted"* ]]
}

pass=0
fail=0
mkdir -p "$OUT_DIR"

while IFS=$'\t' read -r name expected prompt; do
  [[ -z "${name:-}" || "$name" == \#* ]] && continue
  if [[ ${#WANTED[@]} -gt 0 ]] && ! printf '%s\n' "${WANTED[@]}" | grep -qx "$name"; then
    continue
  fi
  if [[ "$LIST_ONLY" == 1 ]]; then
    printf '%-26s → %s\n' "$name" "$expected"
    continue
  fi

  transcript="$OUT_DIR/$name.jsonl"
  "$CLAUDE_BIN" -p "$prompt" \
    --output-format stream-json --verbose \
    --max-turns 8 \
    > "$transcript" 2>"$OUT_DIR/$name.err"
  status=$?

  actual="$(invoked_component "$transcript")"

  if [[ "$status" != 0 && -z "$actual" ]]; then
    printf 'ERROR %-26s claude exited %s: %s\n' "$name" "$status" \
      "$(head -c 160 "$OUT_DIR/$name.err" | tr '\n' ' ')"
    fail=$((fail + 1))
    continue
  fi

  if [[ "$expected" == "none" ]]; then
    if [[ -z "$actual" ]]; then
      printf 'ok    %-26s nothing fired, as intended\n' "$name"
      pass=$((pass + 1))
    else
      printf 'FAIL  %-26s %s fired on a prompt that needs no component\n' \
        "$name" "$actual"
      fail=$((fail + 1))
    fi
  elif matches "$actual" "$expected"; then
    printf 'ok    %-26s %s\n' "$name" "$actual"
    pass=$((pass + 1))
  else
    printf 'FAIL  %-26s wanted %s, got %s\n' "$name" "$expected" \
      "${actual:-nothing}"
    fail=$((fail + 1))
  fi
done < "$CASES"

[[ "$LIST_ONLY" == 1 ]] && exit 0

echo
echo "-------------------------------"
printf '%d routed correctly, %d not. Transcripts in %s\n' "$pass" "$fail" "$OUT_DIR"
[[ "$fail" -eq 0 ]] || exit 1
