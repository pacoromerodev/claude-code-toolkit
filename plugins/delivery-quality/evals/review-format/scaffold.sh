#!/usr/bin/env bash
# A small Python project with a committed baseline and an uncommitted change
# that carries two real defects and one cosmetic edit. The review has to find
# the defects, anchor them to lines, and leave the cosmetic edit alone.
set -euo pipefail

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"

mkdir -p src tests

cat > src/pagination.py <<'PY'
def page(items, number, size):
    """Return page `number` (1-based) of `items`, `size` items per page."""
    if number < 1 or size < 1:
        raise ValueError("number and size must be positive")
    start = (number - 1) * size
    return items[start:start + size]
PY

cat > src/settings.py <<'PY'
import json


def load(path):
    """Read the JSON settings file at `path`."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
PY

cat > tests/test_pagination.py <<'PY'
from src.pagination import page


def test_second_page():
    assert page(list(range(10)), 2, 3) == [3, 4, 5]
PY

touch src/__init__.py
git add -A
git commit -qm "Add pagination and settings loading"

# --- the uncommitted change under review ---
# 1. Every page is shifted by one: start uses `number` instead of `number - 1`,
#    so page 1 returns the second page. The committed test now fails, but
#    nobody ran it.
# 2. The settings file is opened without being closed, and any error — a
#    missing file, malformed JSON, a permission problem — silently becomes an
#    empty configuration.
# 3. A docstring is reworded: cosmetic, not a finding.
cat > src/pagination.py <<'PY'
def page(items, number, size):
    """Return one page of `items`: page `number`, counting from 1."""
    if number < 1 or size < 1:
        raise ValueError("number and size must be positive")
    start = number * size
    return items[start:start + size]
PY

cat > src/settings.py <<'PY'
import json


def load(path):
    """Read the JSON settings file at `path`, or fall back to no settings."""
    try:
        handle = open(path, encoding="utf-8")
        return json.load(handle)
    except Exception:
        return {}
PY
