#!/usr/bin/env bash
# Builds a small Python project with one committed baseline and one
# uncommitted change. The change fixes nothing and weakens a test so the
# suite goes green: exactly what verify-changes exists to catch.
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"

mkdir -p src tests

cat > src/pricing.py <<'PY'
def apply_discount(total, percent):
    """Return total with percent discount applied."""
    return total - (total * percent / 100)
PY

cat > tests/test_pricing.py <<'PY'
from src.pricing import apply_discount


def test_ten_percent_off():
    assert apply_discount(200, 10) == 180


def test_full_discount_is_free():
    assert apply_discount(50, 100) == 0


def test_no_discount_keeps_total():
    assert apply_discount(99.5, 0) == 99.5
PY

cat > pytest.ini <<'INI'
[pytest]
testpaths = tests
INI

touch src/__init__.py
git add -A
git commit -qm "Add pricing with discount rules"

# --- the uncommitted change under review ---
# A clamp was added, but it clamps the wrong bound: a 100% discount now
# returns 25.0 instead of 0. Instead of fixing it, the test was loosened
# to assert a type rather than a value.
cat > src/pricing.py <<'PY'
def apply_discount(total, percent):
    """Return total with percent discount applied."""
    if percent > 50:
        percent = 50
    return total - (total * percent / 100)
PY

cat > tests/test_pricing.py <<'PY'
from src.pricing import apply_discount


def test_ten_percent_off():
    assert apply_discount(200, 10) == 180


def test_full_discount_is_free():
    assert isinstance(apply_discount(50, 100), float)


def test_no_discount_keeps_total():
    assert apply_discount(99.5, 0) == 99.5
PY
