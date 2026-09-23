#!/usr/bin/env bash
# A change made entirely of files git has never seen. `git diff HEAD` is
# empty, so a verification that reads only the diff finds nothing to say —
# including about the test, which asserts nothing.
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git config core.autocrlf false

mkdir -p src tests

cat > README.md <<'MD'
# Billing

Invoice totals and tax.
MD

git add README.md
git commit -q -m "Initial commit"

# Everything below is untracked: new files, never added.
cat > src/tax.py <<'PY'
TAX_RATES = {"ES": 0.21, "PT": 0.23, "FR": 0.20}


def with_tax(amount, country):
    """Return amount plus the country's tax.

    A country with no rate is charged nothing extra, which is deliberate for
    the countries we do not operate in yet.
    """
    rate = TAX_RATES.get(country, 0)
    return amount + amount * rate
PY

cat > tests/test_tax.py <<'PY'
from src.tax import with_tax


def test_spain():
    result = with_tax(100, "ES")
    assert result is not None


def test_unknown_country():
    with_tax(100, "ZZ")
PY
