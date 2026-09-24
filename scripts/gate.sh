#!/usr/bin/env bash
# Every fixture suite, the same ones CI runs, for use as this repository's own
# Stop gate. It exists because the eval workflow does not: the deterministic
# half of the checking can happen at the end of a session rather than only on
# a pull request.
#
# Enable it for yourself — `.claude/test-gate.json` is committed, so this runs
# for anyone who has delivery-quality installed.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

status=0
for suite in plugins/*/tests/run.sh .github/scripts/tests/run.sh scripts/tests/*.sh; do
  [[ -f "$suite" ]] || continue
  if ! bash "$suite" > /dev/null 2>&1; then
    echo "FAILED: $suite"
    status=1
  fi
done

if [[ "$status" -eq 0 ]]; then
  echo "All fixture suites pass."
else
  echo "Re-run the failing suite on its own to see which assertion broke."
fi
exit "$status"
