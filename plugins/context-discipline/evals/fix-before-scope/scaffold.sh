#!/usr/bin/env bash
# A payments module with enough surface to wander through, and a history in
# which several things changed on the Tuesday in question. Nothing in the code
# alone says which change broke "some customers".
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git config core.autocrlf false

mkdir -p payments tests

cat > payments/__init__.py <<'PY'
PY

cat > payments/gateway.py <<'PY'
import os

TIMEOUT = float(os.environ.get("GATEWAY_TIMEOUT", "8"))


def charge(card_token, amount_minor, currency):
    """Send a charge to the gateway. Returns the gateway's reference."""
    raise NotImplementedError("network call")
PY

cat > payments/currency.py <<'PY'
MINOR_UNITS = {"EUR": 2, "USD": 2, "GBP": 2, "JPY": 0}


def to_minor(amount, currency):
    return round(amount * 10 ** MINOR_UNITS[currency])
PY

cat > payments/checkout.py <<'PY'
from payments.currency import to_minor
from payments.gateway import charge


def pay(order):
    amount = to_minor(order["total"], order["currency"])
    return charge(order["card_token"], amount, order["currency"])
PY

cat > tests/test_currency.py <<'PY'
from payments.currency import to_minor


def test_euro():
    assert to_minor(12.34, "EUR") == 1234
PY

git add -A
GIT_AUTHOR_DATE="2026-09-10T10:00:00" GIT_COMMITTER_DATE="2026-09-10T10:00:00" \
  git commit -q -m "Payments module"

# Tuesday: three unrelated changes land.
sed -i 's/"8"/"3"/' payments/gateway.py
git commit -qam "Lower the gateway timeout"  --date "2026-09-15T09:12:00"

cat >> payments/currency.py <<'PY'
MINOR_UNITS["CHF"] = 2
MINOR_UNITS["KWD"] = 3
PY
git commit -qam "Support CHF and KWD" --date "2026-09-15T11:40:00"

cat >> payments/checkout.py <<'PY'


def pay_saved(customer, order):
    order = dict(order, card_token=customer["default_card"])
    return pay(order)
PY
git commit -qam "Pay with a saved card" --date "2026-09-15T16:05:00"
