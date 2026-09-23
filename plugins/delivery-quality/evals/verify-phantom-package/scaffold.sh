#!/usr/bin/env bash
# The change imports a package that does not exist. The tests pass, because
# the module that imports it is never imported by a test.
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git config core.autocrlf false

mkdir -p src tests

cat > requirements.txt <<'TXT'
requests==2.32.3
TXT

cat > src/orders.py <<'PY'
def total(lines):
    """Return the order total from its lines."""
    return sum(line["price"] * line["quantity"] for line in lines)
PY

cat > tests/test_orders.py <<'PY'
from src.orders import total


def test_total():
    assert total([{"price": 10, "quantity": 2}, {"price": 5, "quantity": 1}]) == 25
PY

git add -A
git commit -q -m "Order totals"

# The uncommitted change: a new module and a new dependency.
cat > requirements.txt <<'TXT'
requests==2.32.3
py-retryflow==1.4.0
TXT

cat > src/retry.py <<'PY'
from py_retryflow import RetryPolicy, backoff


POLICY = RetryPolicy(attempts=5, wait=backoff.exponential(base=0.5))


def with_retries(call):
    """Run `call` under the shared retry policy."""
    return POLICY.wrap(call)
PY
