#!/usr/bin/env bash
# Fixture tests for the settings checker.
#
# The reference templates this plugin ships are checked too: a plugin whose own
# examples fail its own checker is not one anyone should copy from.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$HERE/../scripts/check_settings.py"
FIXTURES="$HERE/fixtures"
TEMPLATES="$HERE/../settings"
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

# `return 0`: ((pass++)) yields the pre-increment value, tripping `|| bad`.
ok()  { printf 'ok    %-9s %s\n' "$1" "$2"; pass=$((pass + 1)); return 0; }
bad() { printf 'FAIL  %-9s %s\n' "$1" "$2"; fail=$((fail + 1)); return 0; }

bad_output="$("$PY" "$CHECK" "$FIXTURES/bad-settings.json" --managed 2>&1)"
bad_code=$?
good_output="$("$PY" "$CHECK" "$FIXTURES/good-settings.json" --managed 2>&1)"
good_code=$?
invalid_output="$("$PY" "$CHECK" "$FIXTURES/invalid.json" 2>&1)"
invalid_code=$?

echo "== planted faults must all be found =="
for probe in "broad-allow:broad-allow" \
             "bypass-default:bypass-default" \
             "dangerous-flag:dangerous-flag" \
             "secret-value:secret-value" \
             "secret-key:secret-key" \
             "relative-hook:relative-hook" \
             "no-deny:no-deny" \
             "open-marketplaces:open-marketplaces" \
             "no-timeout:no-timeout"; do
  label="${probe%%:*}"; needle="${probe#*:}"
  [[ "$bad_output" == *"$needle"* ]] && ok finds "$label" || bad finds "$label"
done

echo
echo "== the messages explain the consequence =="
[[ "$bad_output" == *"should be treated as leaked"* ]] \
  && ok says "a literal credential is called leaked, not just flagged" \
  || bad says "credential message is bare"
[[ "$bad_output" == *"directory the session started in"* ]] \
  && ok says "relative hook path explains why it silently fails" \
  || bad says "relative hook message is bare"

echo
echo "== the good file must produce nothing =="
if [[ "$good_output" == *"Clean —"* ]]; then
  ok quiet "no findings at all"
else
  bad quiet "reported: $(printf '%s' "$good_output" | head -2 | tr '\n' ' ')"
fi

echo
echo "== the marketplace allowlist =="
bool_output="$("$PY" "$CHECK" "$FIXTURES/bad-marketplace-bool.json" --managed 2>&1)"
bool_code=$?
for probe in "strict-not-a-list:strictKnownMarketplaces is bool" \
             "unknown-setting:there is no knownMarketplaces setting" \
             "unpinned-marketplace:registered from a git source with no ref"; do
  label="${probe%%:*}"; needle="${probe#*:}"
  [[ "$bool_output" == *"$needle"* ]] && ok finds "$label" || bad finds "$label"
done
[[ "$bool_code" == 1 ]] && ok exit "a rejected allowlist is an error (1)" \
                        || bad exit "wanted 1, got $bool_code"

echo
echo "== invalid JSON =="
[[ "$invalid_output" == *"invalid-json"* ]] \
  && ok finds "a settings file that cannot be parsed" || bad finds "invalid json"
[[ "$invalid_output" == *"silently"* ]] \
  && ok says "explains that the rules stop applying with no message" \
  || bad says "does not say the failure is silent"
[[ "$invalid_code" == 1 ]] \
  && ok exit "invalid JSON is an error (1)" || bad exit "wanted 1, got $invalid_code"

echo
echo "== exit codes =="
[[ "$bad_code" == 1 ]] && ok exit "errors present (1)" || bad exit "wanted 1, got $bad_code"
[[ "$good_code" == 0 ]] && ok exit "nothing wrong (0)" || bad exit "wanted 0, got $good_code"

echo
echo "== the shipped templates must pass their own checker =="
managed="$("$PY" "$CHECK" "$TEMPLATES/managed-settings.json" --managed 2>&1)"
[[ "$managed" == *"Clean —"* ]] \
  && ok templates "managed-settings.json is clean" \
  || bad templates "managed template: $(printf '%s' "$managed" | head -2 | tr '\n' ' ')"

project="$("$PY" "$CHECK" "$TEMPLATES/project-settings.json" 2>&1)"
[[ "$project" == *"Clean —"* ]] \
  && ok templates "project-settings.json is clean" \
  || bad templates "project template: $(printf '%s' "$project" | head -2 | tr '\n' ' ')"

# The templates carry $comment keys; those must not be mistaken for settings.
[[ "$managed" != *"secret"* ]] \
  && ok templates "comment keys are not read as values" \
  || bad templates "a \$comment key was flagged"

echo
echo "== json output =="
json="$("$PY" "$CHECK" "$FIXTURES/bad-settings.json" --managed --json 2>/dev/null)"
if printf '%s' "$json" | "$PY" -c \
   'import json,sys; d=json.load(sys.stdin); assert d["errors"]>0 and d["findings"]'; then
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
