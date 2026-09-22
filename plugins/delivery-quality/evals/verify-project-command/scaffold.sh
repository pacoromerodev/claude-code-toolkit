#!/usr/bin/env bash
# The project declares how its tests run, and it is not what the file layout
# would suggest: pytest alone collects nothing, because the suite lives under
# checks/ and is driven by a runner script.
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git config core.autocrlf false

mkdir -p src checks .claude

cat > src/shipping.py <<'PY'
def band(weight_kg):
    """Return the shipping band for a parcel weight in kilograms."""
    if weight_kg <= 1:
        return "letter"
    if weight_kg <= 10:
        return "parcel"
    return "freight"
PY

cat > checks/check_bands.py <<'PY'
"""The project's own checks. Run through .claude/test-gate.json."""
import sys

sys.path.insert(0, ".")

from src.shipping import band


def main():
    failures = []
    for weight, expected in ((0.5, "letter"), (1, "letter"), (5, "parcel"),
                             (10, "parcel"), (10.5, "freight")):
        actual = band(weight)
        if actual != expected:
            failures.append(f"band({weight}) was {actual!r}, wanted {expected!r}")
    for failure in failures:
        print(failure)
    print(f"{5 - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
PY

cat > .claude/test-gate.json <<'JSON'
{
  "command": ["python3", "checks/check_bands.py"],
  "timeout": 120
}
JSON

git add -A
git commit -q -m "Shipping bands and their checks"

# The uncommitted change: the boundary moves, and the check now fails.
cat > src/shipping.py <<'PY'
def band(weight_kg):
    """Return the shipping band for a parcel weight in kilograms."""
    if weight_kg < 1:
        return "letter"
    if weight_kg < 10:
        return "parcel"
    return "freight"
PY
