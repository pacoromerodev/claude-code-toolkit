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
printf '#!/usr/bin/env bash\necho "$*" >> "%s/calls"\n' "$SANDBOX" > "$stub"
chmod +x "$stub"

# Two homes: one whose Docker store holds a symlink, one whose store is plain.
mkdir -p "$SANDBOX/linked/.docker" "$SANDBOX/plain/.docker" "$SANDBOX/elsewhere"
ln -s "$SANDBOX/elsewhere" "$SANDBOX/linked/.docker/contexts"
: > "$SANDBOX/plain/.docker/config.json"

# Count the cases of one plugin, and how many of them need Bash.
plugin=skill-forge
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
printf '%d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
