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
check guard_secrets.py edge-multiedit.json        2 "Anthropic API key"

echo
echo "== guard_secrets: blocked paths =="
check guard_secrets.py path-dotenv.json           2 "credentials"
check guard_secrets.py path-ssh-key.json          2 "credentials"
check guard_secrets.py path-aws-credentials.json  2 "credentials"
check guard_secrets.py path-pem-write.json        2 "credentials"
check guard_secrets.py path-bash-redirect-env.json 2 "credentials"
check guard_secrets.py path-bash-tee-credentials.json 2 "credentials"

echo
echo "== guard_secrets: must let through =="
check guard_secrets.py ok-env-lookup.json         0
check guard_secrets.py ok-aws-example-key.json    0
check guard_secrets.py ok-placeholder.json        0
check guard_secrets.py ok-variable-named-token.json 0
check guard_secrets.py ok-plain-edit.json         0
check guard_secrets.py ok-jwt-in-docs.json        0
check guard_secrets.py ok-bash-normal-redirect.json 0

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
echo "== guard_destructive: must fail open =="
check guard_destructive.py destr-malformed.json       0
check guard_destructive.py destr-no-command.json      0

echo
echo "== test_gate =="
check test_gate.py gate-no-marker.json            0
check test_gate.py gate-reentry.json              0
check test_gate.py gate-malformed.json            0

echo
echo "-------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
