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
finds "a body pointing at a file nobody ships" "points at \`docs/anatomy.md\`"
finds "overlapping descriptions"         "overlaps"
finds "bare Bash, comma-separated"       "grant-bare-comma: \`allowed-tools\` pre-approves every shell command"
finds "bare Bash, space-separated"       "grant-bare-space: \`allowed-tools\` pre-approves every shell command"
finds "bare Bash, flow list"             "grant-bare-flow: \`allowed-tools\` pre-approves every shell command"
finds "bare Bash, YAML block list"       "grant-bare-block: \`allowed-tools\` pre-approves every shell command"
finds "pre-approved file writes"         "grant-write: \`allowed-tools\` pre-approves file writes"

echo
echo "== what loads anyway is a warning, not an error =="
# Claude Code loads a skill whose name differs from its directory. The names
# do different jobs — command segment in a plugin, listing label outside one —
# so the disagreement is worth saying, and is not a failure.
mismatch_output="$("$PY" "$AUDIT" "$FIXTURES/broken/name-mismatch" 2>&1)"
code "a name mismatch alone" "$?" 0
if [[ "$mismatch_output" == *"warn"* && "$mismatch_output" != *"ERROR"* ]]; then
  printf 'ok    finds   a name mismatch is reported as a warning\n'; ((pass++))
else
  printf 'FAIL  finds   name mismatch not a warning: %s\n' "${mismatch_output%%$'\n'*}"; ((fail++))
fi

echo
echo "== a SKILL.md loose in a skills root =="
# The root also holds a real skill. Both must be audited: the loose file as an
# error, the real skill as clean. It must not be mistaken for one skill whose
# directory is the root.
loose_output="$("$PY" "$AUDIT" "$FIXTURES/loose" 2>&1)"
loose_code=$?
if [[ "$loose_output" == *"sits loose in the skills root"* ]]; then
  printf 'ok    loose   reported as never loading\n'; ((pass++))
else
  printf 'FAIL  loose   not reported: %s\n' "${loose_output%%$'\n'*}"; ((fail++))
fi
if [[ "$loose_output" != *"but the directory is"* ]]; then
  printf 'ok    loose   not misread as a name mismatch\n'; ((pass++))
else
  printf 'FAIL  loose   misread as a name mismatch\n'; ((fail++))
fi
code "loose file is an error" "$loose_code" 1

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
echo "== a skill competes with the agents and commands beside it =="
# fixtures/neighbours is shaped like a plugin: the command's description is a
# copy of the skill's, and the agent's is unrelated.
neighbours_output="$("$PY" "$AUDIT" "$FIXTURES/neighbours/skills" 2>&1)"
code "a neighbour clash is a warning, not an error" "$?" 0
if [[ "$neighbours_output" == *"overlaps 100% with 'command latency-trace'"* ]]; then
  printf 'ok    finds   a command description copied from the skill\n'; ((pass++))
else
  printf 'FAIL  finds   the duplicated command description:\n%s\n' "$neighbours_output"; ((fail++))
fi
if [[ "$neighbours_output" != *"cost-reviewer"* ]]; then
  printf 'ok    quiet   an unrelated agent beside it\n'; ((pass++))
else
  printf 'FAIL  quiet   reported the unrelated agent\n'; ((fail++))
fi

echo
echo "== subagents are audited too =="
agents_output="$("$PY" "$AUDIT" "$FIXTURES/broken-agents/agents" 2>&1)"
code "a reviewer that can edit is an error" "$?" 1
for probe in "edit tools on a reviewer:a reviewing agent with Edit, Write" \
             "a persona line:persona line:" \
             "no section for gaps:has no section for gaps" \
             "no trigger in the description:never says when to delegate" \
             "nothing about what to pass:never says what to pass" \
             "name not matching the file:but the file is wrong-name.md"; do
  label="${probe%%:*}"; needle="${probe#*:}"
  if [[ "$agents_output" == *"$needle"* ]]; then
    printf 'ok    finds   %s\n' "$label"; ((pass++))
  else
    printf 'FAIL  finds   %s — nothing matched %q\n' "$label" "$needle"; ((fail++))
  fi
done

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
echo "== routing log: opt-in, and what it records =="
routing_project="$(mktemp -d)"
routing_data="$(mktemp -d)"
mkdir -p "$routing_project/.claude"

# routing_send <payload json>  — returns the log's line count
routing_send() {
  printf '%s' "$1" | CLAUDE_PLUGIN_DATA="$routing_data" \
    "$PY" "$HERE/../scripts/log_routing.py" > /dev/null 2>&1
  local log="$routing_data/routing.jsonl"
  [[ -f "$log" ]] && wc -l < "$log" | tr -d ' ' || echo 0
}

prompt_payload="$(printf '{"hook_event_name":"UserPromptSubmit","session_id":"abc12345","cwd":"%s","prompt":"why does my skill never fire"}' "$routing_project")"
skill_payload="$(printf '{"hook_event_name":"PreToolUse","session_id":"abc12345","cwd":"%s","tool_name":"Skill","tool_input":{"skill":"skill-forge:audit-skills"}}' "$routing_project")"
agent_payload="$(printf '{"hook_event_name":"PreToolUse","session_id":"abc12345","cwd":"%s","tool_name":"Task","tool_input":{"subagent_type":"delivery-quality:code-reviewer"}}' "$routing_project")"
other_payload="$(printf '{"hook_event_name":"PreToolUse","session_id":"abc12345","cwd":"%s","tool_name":"Bash","tool_input":{"command":"ls"}}' "$routing_project")"

# Without the marker the hook writes nothing at all.
if [[ "$(routing_send "$prompt_payload")" == "0" ]]; then
  printf 'ok    routing writes nothing until a project opts in\n'; ((pass++))
else
  printf 'FAIL  routing logged without the marker file\n'; ((fail++))
fi

touch "$routing_project/.claude/routing-log"
[[ "$(routing_send "$prompt_payload")" == "1" ]] \
  && { printf 'ok    routing records a prompt once enabled\n'; ((pass++)); } \
  || { printf 'FAIL  routing did not record the prompt\n'; ((fail++)); }
[[ "$(routing_send "$skill_payload")" == "2" ]] \
  && { printf 'ok    routing records a skill that fired\n'; ((pass++)); } \
  || { printf 'FAIL  routing missed the Skill call\n'; ((fail++)); }
[[ "$(routing_send "$agent_payload")" == "3" ]] \
  && { printf 'ok    routing records a subagent that fired\n'; ((pass++)); } \
  || { printf 'FAIL  routing missed the Task call\n'; ((fail++)); }
# A tool that says nothing about routing must not become a row.
[[ "$(routing_send "$other_payload")" == "3" ]] \
  && { printf 'ok    routing ignores an unrelated tool\n'; ((pass++)); } \
  || { printf 'FAIL  routing logged a Bash call\n'; ((fail++)); }
# Malformed input must not break the session.
[[ "$(routing_send 'not json')" == "3" ]] \
  && { printf 'ok    routing fails open on malformed input\n'; ((pass++)); } \
  || { printf 'FAIL  routing reacted to malformed input\n'; ((fail++)); }

# The log never lands inside the project being worked in.
if [[ -z "$(find "$routing_project" -name 'routing.jsonl' 2>/dev/null)" ]]; then
  printf 'ok    routing keeps the log out of the project\n'; ((pass++))
else
  printf 'FAIL  routing wrote the log into the project\n'; ((fail++))
fi

report="$("$PY" "$HERE/../scripts/routing_report.py" "$routing_data/routing.jsonl" 2>&1)"
[[ "$report" == *"skill-forge:audit-skills"* && "$report" == *"delivery-quality:code-reviewer"* ]] \
  && { printf 'ok    routing report names what fired\n'; ((pass++)); } \
  || { printf 'FAIL  routing report: %s\n' "${report%%$'\n'*}"; ((fail++)); }

# A prompt with nothing after it is the row worth reading.
silent_project="$(mktemp -d)"; silent_data="$(mktemp -d)"
mkdir -p "$silent_project/.claude" && touch "$silent_project/.claude/routing-log"
printf '{"hook_event_name":"UserPromptSubmit","session_id":"zz","cwd":"%s","prompt":"this description matches nothing"}' "$silent_project" \
  | CLAUDE_PLUGIN_DATA="$silent_data" "$PY" "$HERE/../scripts/log_routing.py" > /dev/null 2>&1
silent_report="$("$PY" "$HERE/../scripts/routing_report.py" "$silent_data/routing.jsonl" 2>&1)"
[[ "$silent_report" == *"fired nothing: 1 of 1"* ]] \
  && { printf 'ok    routing report counts a prompt that fired nothing\n'; ((pass++)); } \
  || { printf 'FAIL  routing report missed the silent prompt\n'; ((fail++)); }
rm -r -f "$routing_project" "$routing_data" "$silent_project" "$silent_data"
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
