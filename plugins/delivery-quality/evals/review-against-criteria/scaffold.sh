#!/usr/bin/env bash
# The task states four acceptance criteria. The change satisfies three, the
# tests cover those three and pass, and the fourth was never implemented.
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git config core.autocrlf false

mkdir -p src tests

cat > TASK.md <<'MD'
# Export subscribers to CSV

Acceptance criteria:

1. The export contains every active subscriber, and no cancelled one.
2. Columns are id, email, plan, renewed_on, in that order.
3. Dates are written as YYYY-MM-DD.
4. An export of more than 10,000 rows is written in batches, so memory does
   not grow with the export.
MD

cat > src/export.py <<'PY'
def rows(subscribers):
    """Return the rows for the export."""
    return [s for s in subscribers if s["status"] == "active"]
PY

cat > tests/test_export.py <<'PY'
from src.export import rows


def test_only_active():
    given = [{"status": "active", "id": 1}, {"status": "cancelled", "id": 2}]
    assert [row["id"] for row in rows(given)] == [1]
PY

git add -A
git commit -q -m "Export skeleton and its task"

# The uncommitted change.
cat > src/export.py <<'PY'
import csv

COLUMNS = ["id", "email", "plan", "renewed_on"]


def rows(subscribers):
    """Return the active subscribers, in export order."""
    return [s for s in subscribers if s["status"] == "active"]


def write_csv(subscribers, handle):
    """Write every active subscriber to `handle` as CSV."""
    writer = csv.writer(handle)
    writer.writerow(COLUMNS)
    exported = [
        [row["id"], row["email"], row["plan"], row["renewed_on"].strftime("%Y-%m-%d")]
        for row in rows(subscribers)
    ]
    writer.writerows(exported)
    return len(exported)
PY

cat > tests/test_export.py <<'PY'
import io
from datetime import date

from src.export import rows, write_csv


def subscriber(id, status="active"):
    return {"id": id, "email": f"{id}@example.invalid", "plan": "pro",
            "status": status, "renewed_on": date(2026, 3, 4)}


def test_only_active():
    given = [subscriber(1), subscriber(2, "cancelled")]
    assert [row["id"] for row in rows(given)] == [1]


def test_columns_and_dates():
    handle = io.StringIO()
    write_csv([subscriber(1)], handle)
    lines = handle.getvalue().splitlines()
    assert lines[0] == "id,email,plan,renewed_on"
    assert lines[1].endswith("2026-03-04")
PY
