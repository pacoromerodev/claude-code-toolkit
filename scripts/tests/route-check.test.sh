#!/usr/bin/env bash
# route_check.sh against a stub `claude`, so the reading of a transcript is
# tested without paying for a session.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$HERE/../route_check.sh"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

pass=0
fail=0
ok()  { printf 'ok    %-34s %s\n' "$1" "$2"; pass=$((pass + 1)); }
bad() { printf 'FAIL  %-34s %s\n' "$1" "$2"; fail=$((fail + 1)); }

# The stub answers by prompt: it prints the transcript the real CLI would emit
# for a session that invoked a given component, or one that invoked nothing.
stub="$SANDBOX/claude"
cat > "$stub" <<'STUB'
#!/usr/bin/env bash
prompt=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p) prompt="$2"; shift 2 ;;
    *) shift ;;
  esac
done
emit_skill() {
  printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"%s"}}]}}\n' "$1"
}
emit_agent() {
  printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Agent","input":{"subagent_type":"%s"}}]}}\n' "$1"
}
emit_task() {
  printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Task","input":{"subagent_type":"%s"}}]}}\n' "$1"
}
case "$prompt" in
  *"Can you confirm it actually works"*) emit_skill "delivery-quality:verify-changes" ;;
  *"get_invoice"*) emit_agent "api-patterns:tool-schema-review" ;;
  *"second opinion"*) emit_task "delivery-quality:code-reviewer" ;;
  *"slash command"*) printf '{"type":"assistant","message":{"content":"A skill fires on its own; a command is typed."}}\n' ;;
  *"retrieval"*) emit_skill "api-patterns:prompt-cache-audit" ;;
  *) printf '{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]}}\n' ;;
esac
STUB
chmod +x "$stub"

run_case() {
  CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/out" bash "$RUNNER" "$1" 2>&1
}

out="$(run_case verify-the-change)"
[[ "$out" == *"ok    verify-the-change"* ]] \
  && ok "a skill that fired" "read from the transcript" \
  || bad "a skill that fired" "$out"

out="$(run_case review-the-diff)"
[[ "$out" == *"ok    review-the-diff"* ]] \
  && ok "a subagent that fired" "read from the Task block" \
  || bad "a subagent that fired" "$out"

# Current Claude Code calls the subagent tool Agent. Reading only Task made
# every delegation look like nothing fired.
out="$(run_case api-tools-ignored)"
[[ "$out" == *"ok    api-tools-ignored"* ]] \
  && ok "a subagent through Agent" "read from the Agent block" \
  || bad "a subagent through Agent" "$out"

# The real CLI sends `content` as a plain string on a text-only turn, and as
# a list of blocks only when a tool is used. Reading the string form as a list
# is what broke the first live run.
out="$(run_case plain-question)"
[[ "$out" == *"ok    plain-question"* && "$out" == *"nothing fired"* ]] \
  && ok "a text-only turn" "read as firing nothing, not as an error" \
  || bad "a text-only turn" "$out"
[[ "$out" != *"Traceback"* ]] \
  && ok "a text-only turn" "does not raise" \
  || bad "a text-only turn" "the parser raised"

# The stub deliberately routes the retrieval question to the caching skill:
# the wrong component, which is exactly the collision this script exists for.
out="$(run_case retrieval-misses)"
if [[ "$out" == *"FAIL  retrieval-misses"* && "$out" == *"wanted rag-retriever"* ]]; then
  ok "the wrong component" "named, with what was wanted"
else
  bad "the wrong component" "$out"
fi

out="$(CLAUDE_BIN="$stub" OUT_DIR="$SANDBOX/out2" bash "$RUNNER" retrieval-misses 2>&1)"
code=$?
[[ "$code" == 1 ]] && ok "a mis-route" "exits 1" || bad "a mis-route" "exit $code"

out="$(CLAUDE_BIN="$stub" bash "$RUNNER" --list 2>&1)"
[[ "$out" == *"verify-the-change"* && "$out" != *"ok    "* ]] \
  && ok "--list" "prints the cases without running them" \
  || bad "--list" "$out"

# A missing CLI must be reported, not counted as a pass.
out="$(CLAUDE_BIN="$SANDBOX/not-here" OUT_DIR="$SANDBOX/out3" bash "$RUNNER" plain-question 2>&1)"
[[ "$out" == *"ERROR"* ]] \
  && ok "no claude on PATH" "reported as an error" \
  || bad "no claude on PATH" "$out"

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
