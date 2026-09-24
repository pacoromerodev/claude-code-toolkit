#!/usr/bin/env bash
# Fixture tests for the delivery-quality hooks.
#
# Each case feeds a payload from fixtures/ to a hook script and asserts the
# exit code, and where it matters a substring of stderr. Exit 2 means the hook
# blocked; anything else means it let the call through.
#
# Run: plugins/delivery-quality/tests/run.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$HERE/../scripts"
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

# check <script> <fixture> <expected exit> [expected stderr substring]
check() {
  local script="$1" fixture="$2" want="$3" needle="${4:-}"
  local out code

  out="$("$PY" "$SCRIPTS/$script" < "$FIXTURES/$fixture" 2>&1)"
  code=$?

  if [[ "$code" != "$want" ]]; then
    printf 'FAIL  %-28s %-26s exit %s, wanted %s\n' "$script" "$fixture" "$code" "$want"
    [[ -n "$out" ]] && printf '        output: %s\n' "${out%%$'\n'*}"
    ((fail++))
    return
  fi

  if [[ -n "$needle" && "$out" != *"$needle"* ]]; then
    printf 'FAIL  %-28s %-26s exit %s but stderr lacks %q\n' "$script" "$fixture" "$code" "$needle"
    printf '        output: %s\n' "${out%%$'\n'*}"
    ((fail++))
    return
  fi

  printf 'ok    %-28s %s\n' "$script" "$fixture"
  ((pass++))
}

echo "== guard_secrets: must block =="
check guard_secrets.py secret-anthropic-key.json  2 "Anthropic API key"
check guard_secrets.py secret-aws-key.json        2 "AWS access key id"
check guard_secrets.py secret-github-token.json   2 "GitHub token"
check guard_secrets.py secret-private-key.json    2 "private key"
check guard_secrets.py secret-jdbc-password.json  2 "JDBC"
check guard_secrets.py secret-conn-string.json    2 "connection string"
check guard_secrets.py secret-gcp-sa.json        2 "GCP service account"
check guard_secrets.py secret-azure-storage.json  2 "Azure storage key"
check guard_secrets.py secret-jwt.json            2 "signed JWT"
check guard_secrets.py secret-basic-auth.json     2 "Basic auth header"
check guard_secrets.py secret-npm-token.json      2 "npm token"
check guard_secrets.py secret-notebook-source.json 2 "AWS access key id"
check guard_secrets.py secret-github-fine-grained.json 2 "GitHub fine-grained token"
check guard_secrets.py secret-bash-append.json    2 "this command line"

echo
echo "== guard_secrets: blocked paths =="
check guard_secrets.py path-dotenv.json           2 "credential file"
check guard_secrets.py path-ssh-key.json          2 "credential file"
check guard_secrets.py path-aws-credentials.json  2 "credential file"
check guard_secrets.py path-pem-write.json        2 "credential file"
check guard_secrets.py path-bash-redirect-env.json 2 "credential file"
check guard_secrets.py path-bash-tee-credentials.json 2 "credential file"
check guard_secrets.py path-noclobber-env.json    2 "credential file"
check guard_secrets.py path-install-ssh-key.json  2 "credential file"
check guard_secrets.py path-windows-env.json      2 "credential file"
check guard_secrets.py path-guard-allow-write.json 2 "exception list"
check guard_secrets.py path-destructive-allow-bash.json 2 "exception list"

echo
echo "== guard_secrets: must let through =="
check guard_secrets.py ok-env-lookup.json         0
check guard_secrets.py ok-aws-example-key.json    0
check guard_secrets.py ok-placeholder.json        0
check guard_secrets.py ok-variable-named-token.json 0
check guard_secrets.py ok-plain-edit.json         0
check guard_secrets.py ok-jwt-in-docs.json        0
check guard_secrets.py ok-bash-normal-redirect.json 0
check guard_secrets.py ok-grep-literal-key.json   0
check guard_secrets.py ok-git-log-search.json     0
check guard_secrets.py ok-env-example.json        0
check guard_secrets.py ok-url-with-at-path.json   0

echo
echo "== guard_secrets: must fail open =="
check guard_secrets.py edge-malformed.json        0
check guard_secrets.py edge-empty-input.json      0
check guard_secrets.py edge-no-tool-input.json    0

echo
echo "== guard_destructive: must block =="
check guard_destructive.py destr-rm-home.json         2 "outside the project"
check guard_destructive.py destr-rm-root.json         2 "outside the project"
check guard_destructive.py destr-force-push-main.json 2 "rewrites history"
check guard_destructive.py destr-git-clean.json       2 "untracked"
check guard_destructive.py destr-branch-D.json        2 "unmerged"
check guard_destructive.py destr-drop-table.json      2 "test or local database"
check guard_destructive.py destr-chmod-777.json       2 "world-writable"
check guard_destructive.py destr-terraform.json       2 "auto-approve"
check guard_destructive.py destr-mkfs.json            2 "block device"

echo
echo "== guard_destructive: the forms the first version missed =="
check guard_destructive.py destr-force-push-flag-first.json 2 "rewrites history"
check guard_destructive.py destr-force-push-short.json      2 "rewrites history"
check guard_destructive.py destr-force-push-plus.json       2 "rewrites history"
check guard_destructive.py destr-force-with-lease-main.json 2 "not an alternative"
check guard_destructive.py destr-push-mirror.json           2 "--mirror"
check guard_destructive.py destr-push-delete-main.json      2 "deletes the remote branch main"
check guard_destructive.py destr-rm-uppercase.json          2 "outside the project"
check guard_destructive.py destr-rm-flags-after.json        2 "outside the project"
check guard_destructive.py destr-rm-home-var.json           2 "outside the project"
check guard_destructive.py destr-rm-chained.json            2 "outside the project"
check guard_destructive.py destr-rm-sudo.json               2 "outside the project"
check guard_destructive.py destr-rm-bash-c.json             2 "outside the project"
check guard_destructive.py destr-rm-substitution.json       2 "outside the project"
check guard_destructive.py destr-rm-shell-heredoc.json      2 "outside the project"
check guard_destructive.py destr-find-delete.json           2 "outside the project"
check guard_destructive.py destr-drop-devnull.json          2 "test or local database"
check guard_destructive.py destr-drop-developer.json        2 "test or local database"
check guard_destructive.py destr-delete-mid-command.json    2 "DELETE FROM users"
check guard_destructive.py destr-sql-heredoc.json           2 "TRUNCATE orders"
check guard_destructive.py destr-kubectl-all.json           2 "bulk-deletes"

echo
echo "== guard_destructive: must let through =="
check guard_destructive.py ok-force-with-lease.json   0
check guard_destructive.py ok-rm-in-project.json      0
check guard_destructive.py ok-drop-test-db.json       0
check guard_destructive.py ok-normal-build.json       0
check guard_destructive.py ok-git-status.json         0
check guard_destructive.py ok-heredoc-to-file.json    0
check guard_destructive.py ok-commit-message-rm.json  0
check guard_destructive.py ok-commit-message-sql.json 0
check guard_destructive.py ok-git-clean-dry-run.json  0
check guard_destructive.py ok-delete-with-where.json  0
check guard_destructive.py ok-force-push-feature.json 0

echo
echo "== guard_destructive: against a real repository =="
# reset --hard and checkout . only lose tracked changes. An untracked file —
# such as a state snapshot another hook wrote — must not block them.
repo="$(mktemp -d)"
(
  cd "$repo" || exit 1
  git init -q -b main . && git config user.email t@example.invalid && git config user.name T
  echo one > tracked.txt && git add -A && git commit -qm init
  echo scratch > untracked.txt
) >/dev/null 2>&1
reset_payload="$(printf '{"tool_name":"Bash","tool_input":{"command":"git reset --hard"},"cwd":"%s"}' "$repo")"
code_of() { printf '%s' "$1" | CLAUDE_PROJECT_DIR="$2" "$PY" "$SCRIPTS/guard_destructive.py" >/dev/null 2>&1; echo $?; }
[[ "$(code_of "$reset_payload" "$repo")" == 0 ]] && { printf 'ok    %-28s %s\n' guard_destructive.py "reset --hard with only untracked files"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_destructive.py "reset --hard blocked by an untracked file"; ((fail++)); }
echo two > "$repo/tracked.txt"
[[ "$(code_of "$reset_payload" "$repo")" == 2 ]] && { printf 'ok    %-28s %s\n' guard_destructive.py "reset --hard over a tracked change"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_destructive.py "reset --hard over a tracked change not blocked"; ((fail++)); }

# An allow rule exempts the command it matches, not the line it is chained into.
proj="$(mktemp -d)"
mkdir -p "$proj/.claude"
printf '^rm -rf /tmp/build-cache$\n' > "$proj/.claude/destructive-guard-allow"
allowed="$(printf '{"tool_name":"Bash","tool_input":{"command":"rm -r%s /tmp/build-cache"},"cwd":"%s"}' f "$proj")"
chained="$(printf '{"tool_name":"Bash","tool_input":{"command":"rm -r%s /tmp/build-cache && rm -r%s ~/projects"},"cwd":"%s"}' f f "$proj")"
[[ "$(code_of "$allowed" "$proj")" == 0 ]] && { printf 'ok    %-28s %s\n' guard_destructive.py "allow rule exempts its own command"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_destructive.py "allow rule ignored"; ((fail++)); }
[[ "$(code_of "$chained" "$proj")" == 2 ]] && { printf 'ok    %-28s %s\n' guard_destructive.py "allow rule does not cover a chained command"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_destructive.py "allow rule exempted the whole chained line"; ((fail++)); }
rm -r -f "$repo" "$proj"

echo
echo "== guard_secrets: opt-in redaction =="
# Without the marker the guard blocks; with it, the command comes back
# rewritten for the user to confirm. The key is built here rather than written
# out, so no fixture on disk holds a string shaped like a live credential.
redact_probe() {  # redact_probe <project dir>
  "$PY" - "$SCRIPTS/guard_secrets.py" "$1" <<'PY'
import json
import subprocess
import sys

guard, root = sys.argv[1], sys.argv[2]
key = "sk-" + "ant-api03-" + "".join(
    ["Qw3r", "Ty7u", "Iop2", "Asd4", "Fgh6", "Jkl8", "Zxc0", "Vbn1"])
payload = {
    "cwd": root,
    "tool_name": "Bash",
    "tool_input": {
        "command": f"curl -H 'Authorization: Bearer {key}' https://api.example.com/v1/x",
        "description": "call the API",
        "timeout": 30,
    },
}
result = subprocess.run([sys.executable, guard], input=json.dumps(payload),
                        capture_output=True, text=True)
print(result.returncode)
print(json.dumps({"stdout": result.stdout, "leaked": key in result.stdout}))
PY
}

secret_code_of() { printf '%s' "$1" | "$PY" "$SCRIPTS/guard_secrets.py" >/dev/null 2>&1; echo $?; }

redact_project="$(mktemp -d)"
mkdir -p "$redact_project/.claude"

out="$(redact_probe "$redact_project")"
[[ "$(printf '%s' "$out" | head -1)" == 2 ]] \
  && { printf 'ok    %-28s %s\n' guard_secrets.py "blocks when redaction is not enabled"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_secrets.py "did not block without the marker"; ((fail++)); }

touch "$redact_project/.claude/secret-guard-redact"
out="$(redact_probe "$redact_project")"
code="$(printf '%s' "$out" | head -1)"
body="$(printf '%s' "$out" | tail -1)"
verdict="$("$PY" - "$body" <<'PY'
import json
import sys

result = json.loads(sys.argv[1])
if result["leaked"]:
    print("the key came back in the hook's own output")
    raise SystemExit
data = json.loads(result["stdout"])
hook = data.get("hookSpecificOutput", {})
updated = hook.get("updatedInput", {})
problems = []
if hook.get("hookEventName") != "PreToolUse":
    problems.append("hookEventName missing")
if hook.get("permissionDecision") not in {"ask", "allow"}:
    problems.append(f"permissionDecision is {hook.get('permissionDecision')!r}")
if "REDACTED" not in updated.get("command", ""):
    problems.append("the command was not redacted")
if sorted(updated) != ["command", "description", "timeout"]:
    problems.append(f"updatedInput is partial: {sorted(updated)}")
if "https://api.example.com/v1/x" not in updated.get("command", ""):
    problems.append("redaction ate the rest of the command")
print("; ".join(problems))
PY
)"
[[ "$code" == 0 && -z "$verdict" ]] \
  && { printf 'ok    %-28s %s\n' guard_secrets.py "redacts and hands the call back whole"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_secrets.py "exit $code: ${verdict:-no JSON}"; ((fail++)); }

# The marker is a guard file: writing one is the user's decision, not the
# model's.
marker_write="$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s/.claude/secret-guard-redact","content":""},"cwd":"%s"}' "$redact_project" "$redact_project")"
[[ "$(secret_code_of "$marker_write")" == 2 ]] \
  && { printf 'ok    %-28s %s\n' guard_secrets.py "will not enable its own redaction"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' guard_secrets.py "let the model create the redaction marker"; ((fail++)); }
rm -r -f "$redact_project"
echo
echo "== guard_destructive: must fail open =="
check guard_destructive.py destr-malformed.json       0
check guard_destructive.py destr-no-command.json      0

echo
echo "== test_gate =="
check test_gate.py gate-no-marker.json            0
check test_gate.py gate-reentry.json              0
check test_gate.py gate-malformed.json            0

# The gate runs a real command in a real project. Its feedback goes back as
# JSON on stdout — additionalContext keeps the turn going, systemMessage only
# tells the user — so every case here reads stdout, not the exit code.
gate_project() {
  local dir; dir="$(mktemp -d)"
  mkdir -p "$dir/.claude" "$dir/src"
  ( cd "$dir" && git init -q -b main . && git config user.email t@example.invalid \
      && git config user.name T && echo one > src/app.txt && git add -A \
      && git commit -qm init ) >/dev/null 2>&1
  printf '%s' "$dir"
}
gate_run() {  # gate_run <project> [env assignments...]
  local dir="$1"; shift
  printf '{"cwd":"%s","hook_event_name":"Stop"}' "$dir" \
    | env "$@" "$PY" "$SCRIPTS/test_gate.py" 2>/dev/null
}
# The same stop, but one that already followed a block by this hook.
gate_rerun() {  # gate_rerun <project> [env assignments...]
  local dir="$1"; shift
  printf '{"cwd":"%s","hook_event_name":"Stop","stop_hook_active":true}' "$dir" \
    | env "$@" "$PY" "$SCRIPTS/test_gate.py" 2>/dev/null
}
gate_case() {  # gate_case <label> <output> <python assertion>
  if printf '%s' "$2" | "$PY" -c "$3" 2>/dev/null; then
    printf 'ok    %-28s %s\n' test_gate.py "$1"; ((pass++))
  else
    printf 'FAIL  %-28s %s — output: %s\n' test_gate.py "$1" "$2"; ((fail++))
  fi
}

proj="$(gate_project)"
printf '{"command": ["false"]}' > "$proj/.claude/test-gate.json"
gate_case "a failing suite continues the turn" "$(gate_run "$proj")" '
import json,sys
ctx = json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]
assert "exited 1" in ctx and "Do not delete, skip" in ctx
assert "runs again on your next stop" in ctx'

# A verification task ends in a failing suite on purpose. The first block must
# say so, or Claude asks the user for permission instead of reporting.
gate_case "the block tells a verification to report, not ask" "$(gate_run "$proj")" '
import json,sys
ctx = json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]
assert "verify, review or check" in ctx
assert "not verified" in ctx and "permission" in ctx'

# The second stop re-runs the suite — the fix it demanded has to be checked —
# but it must not block again: that is the loop that made a turn whose right
# answer was a report end in Claude negotiating about hook settings.
gate_case "re-entry re-runs and lets the turn end" "$(gate_rerun "$proj")" '
import json,sys
out = json.load(sys.stdin)
assert "hookSpecificOutput" not in out, "blocked a second time"
msg = out["systemMessage"]
assert "again" in msg and "still exits 1" in msg
assert "allowed to end" in msg'

printf '{"command": ["true"]}' > "$proj/.claude/test-gate.json"
[[ -z "$(gate_run "$proj")" ]] && { printf 'ok    %-28s %s\n' test_gate.py "a passing suite says nothing"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' test_gate.py "a passing suite printed something"; ((fail++)); }

# CLAUDE_TEST_GATE_TIMEOUT used to be parsed at import time, so a value like
# 15m took the hook down with a traceback.
out="$(gate_run "$proj" CLAUDE_TEST_GATE_TIMEOUT=15m)"; code=$?
[[ "$code" == 0 && -z "$out" ]] && { printf 'ok    %-28s %s\n' test_gate.py "survives an unparseable timeout"; ((pass++)); } \
  || { printf 'FAIL  %-28s exit %s, output: %s\n' test_gate.py "$code" "$out"; ((fail++)); }

"$PY" - "$SCRIPTS/test_gate.py" <<'PYTHON' && { printf 'ok    %-28s %s\n' test_gate.py "clamps a timeout above the hook's own"; ((pass++)); } || { printf 'FAIL  %-28s %s\n' test_gate.py "timeout not clamped"; ((fail++)); }
import importlib.util, sys
spec = importlib.util.spec_from_file_location("tg", sys.argv[1])
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
assert gate.effective_timeout({"timeout": 1800}) == gate.TIMEOUT_CEILING
assert gate.effective_timeout({"timeout": 120}) == 120
PYTHON

# only_when_changed must see work that was already committed this session.
printf '{"command": ["false"], "only_when_changed": ["src/**"]}' > "$proj/.claude/test-gate.json"
remote="$(mktemp -d)/origin.git"
( cd "$proj" && git init -q --bare "$remote" && git remote add origin "$remote" \
    && git push -q -u origin main && echo two > src/app.txt && git add -A \
    && git commit -qm "change src" ) >/dev/null 2>&1
gate_case "runs for a change already committed" "$(gate_run "$proj")" '
import json,sys
assert "exited 1" in json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]'

( cd "$proj" && git push -q origin main && echo note > README.md ) >/dev/null 2>&1
[[ -z "$(gate_run "$proj")" ]] && { printf 'ok    %-28s %s\n' test_gate.py "silent when nothing it watches changed"; ((pass++)); } \
  || { printf 'FAIL  %-28s %s\n' test_gate.py "ran for an unrelated change"; ((fail++)); }

# A gate that cannot run must say so to the user, not disappear.
bare="$(gate_project)"; touch "$bare/.claude/test-gate"
gate_case "reports an enabled gate with no runner" "$(gate_run "$bare")" '
import json,sys
assert "did not run" in json.load(sys.stdin)["systemMessage"]'

printf 'not json' > "$bare/.claude/test-gate.json"
gate_case "reports an unreadable config" "$(gate_run "$bare")" '
import json,sys
assert "not valid JSON" in json.load(sys.stdin)["systemMessage"]'

# One enormous failure line must not become the context.
"$PY" - "$proj/.claude/test-gate.json" <<'PYTHON'
import json, sys
script = "python3 -c \"print('FAILED ' + 'x' * 200000)\"; exit 1"
sys.argv[1] and open(sys.argv[1], "w").write(json.dumps({"command": ["bash", "-c", script]}))
PYTHON
gate_case "bounds enormous output" "$(gate_run "$proj")" '
import json,sys
ctx = json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]
assert len(ctx) < 6000, "additionalContext is %d characters" % len(ctx)'

echo
echo "== the tree Claude is in, not the one the session started in =="
# CLAUDE_PROJECT_DIR stays at the session's starting directory; the payload's
# cwd follows Claude into a worktree. A hook that trusts the variable checks
# the wrong tree: a clean main checkout while the worktree has the failure.
main_checkout="$(gate_project)"
tree="$(mktemp -d)/wt"
( cd "$main_checkout" && git worktree add -q --detach "$tree" HEAD \
    && printf '{"command": ["false"]}' > "$tree/.claude/test-gate.json" ) >/dev/null 2>&1
mkdir -p "$tree/.claude" && printf '{"command": ["false"]}' > "$tree/.claude/test-gate.json"
worktree_out="$(printf '{"cwd":"%s","hook_event_name":"Stop"}' "$tree" \
  | env CLAUDE_PROJECT_DIR="$main_checkout" "$PY" "$SCRIPTS/test_gate.py" 2>/dev/null)"
gate_case "test_gate uses the worktree it was called in" "$worktree_out" '
import json,sys
assert "exited 1" in json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]'

echo two > "$tree/src/app.txt"
reset_in_tree="$(printf '{"tool_name":"Bash","tool_input":{"command":"git reset --hard"},"cwd":"%s"}' "$tree")"
if [[ "$(printf '%s' "$reset_in_tree" | env CLAUDE_PROJECT_DIR="$main_checkout" "$PY" "$SCRIPTS/guard_destructive.py" >/dev/null 2>&1; echo $?)" == 2 ]]; then
  printf 'ok    %-28s %s\n' guard_destructive.py "sees changes in the worktree, not the start directory"; ((pass++))
else
  printf 'FAIL  %-28s %s\n' guard_destructive.py "checked the wrong tree"; ((fail++))
fi
( cd "$main_checkout" && git worktree remove --force "$tree" ) >/dev/null 2>&1
rm -r -f "$proj" "$bare" "$remote" "$main_checkout"

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
