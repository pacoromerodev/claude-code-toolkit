#!/usr/bin/env bash
# Fixture tests for the MCP server auditor.
#
# fixtures/bad_server.py plants one fault per primitive; fixtures/good_server.py
# is what the scaffold skill produces and must come back silent.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$HERE/../scripts/check_mcp_server.py"
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

# `return 0` is deliberate: `((pass++))` yields the pre-increment value, so the
# first call would return 1 and trip the `|| bad` branch below.
ok()  { printf 'ok    %-8s %s\n' "$1" "$2"; pass=$((pass + 1)); return 0; }
bad() { printf 'FAIL  %-8s %s\n' "$1" "$2"; fail=$((fail + 1)); return 0; }

bad_output="$("$PY" "$CHECK" "$FIXTURES/bad_server.py" 2>&1)"
bad_code=$?
good_output="$("$PY" "$CHECK" "$FIXTURES/good_server.py" 2>&1)"
good_code=$?

echo "== planted faults must all be found =="
for probe in "untyped-param:untyped-param" \
             "secret-parameter:secret-parameter" \
             "unchecked-path:unchecked-path" \
             "secret-in-uri:secret-in-uri" \
             "thin-description:thin-description" \
             "no-selection-cue:no-selection-cue" \
             "vague-param:vague-param" \
             "unbounded-result:unbounded-result" \
             "no-progress:no-progress" \
             "stateless-note:stateless"; do
  label="${probe%%:*}"; needle="${probe#*:}"
  [[ "$bad_output" == *"$needle"* ]] && ok finds "$label" || bad finds "$label"
done

echo
echo "== the messages explain the consequence =="
[[ "$bad_output" == *"does not hold your secrets"* ]] \
  && ok says "credential parameter explains why it is wrong" \
  || bad says "credential parameter message is bare"
[[ "$bad_output" == *"SDK does not enforce"* ]] \
  && ok says "unchecked path names the SDK's limit" \
  || bad says "unchecked path message is bare"

echo
echo "== the good server must produce nothing =="
if [[ "$good_output" == *"Clean —"* ]]; then
  ok quiet "no findings at all"
else
  bad quiet "reported: $(printf '%s' "$good_output" | head -2 | tr '\n' ' ')"
fi

# Resources and prompts are not held to the tool-length description rule.
[[ "$good_output" != *"thin-description"* ]] \
  && ok quiet "short resource and prompt descriptions are accepted" \
  || bad quiet "flagged a resource or prompt description as thin"

echo
echo "== exit codes =="
[[ "$bad_code" == 1 ]] && ok exit "errors present (1)" || bad exit "wanted 1, got $bad_code"
[[ "$good_code" == 0 ]] && ok exit "nothing wrong (0)" || bad exit "wanted 0, got $good_code"

echo
echo "== stateless conflict detection =="
conflict="$(mktemp -d)/srv.py"
cat > "$conflict" <<'PY'
from mcp.server.fastmcp import Context, FastMCP

mcp = FastMCP("x", stateless_http=True)


@mcp.tool()
async def crawl_site(url: str, ctx: Context) -> str:
    """Crawl a site and index every page found, returning a count.

    Use when the user asks to index a site. Returns the page count; raises
    RuntimeError when the site is unreachable.
    """
    await ctx.report_progress(1, 10)
    await ctx.session.create_message(messages=[], max_tokens=10)
    return "ok"
PY
conflict_output="$("$PY" "$CHECK" "$conflict" 2>&1)"
conflict_code=$?
[[ "$conflict_output" == *"stateless-conflict"* ]] \
  && ok finds "stateless mode used together with sampling and progress" \
  || bad finds "stateless conflict not detected"
[[ "$conflict_output" == *"sampling"* && "$conflict_output" == *"progress"* ]] \
  && ok says "names both features that stop working" \
  || bad says "does not name the broken features"
[[ "$conflict_code" == 1 ]] \
  && ok exit "stateless conflict is an error (1)" \
  || bad exit "wanted 1, got $conflict_code"
rm -rf "$(dirname "$conflict")"

echo
echo "== json output =="
json="$("$PY" "$CHECK" "$FIXTURES/bad_server.py" --json 2>/dev/null)"
if printf '%s' "$json" | "$PY" -c \
   'import json,sys; d=json.load(sys.stdin); assert d["errors"]>0 and d["findings"] and d["primitives"]>0'; then
  ok json "parses and reports findings"
else
  bad json "not valid JSON, or reports nothing"
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
