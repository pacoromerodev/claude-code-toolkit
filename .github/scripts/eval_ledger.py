#!/usr/bin/env python3
"""What each eval case last scored, and whether it has changed since.

An eval costs money or plan usage, so it runs when someone decides to run it.
The failure mode of that arrangement is silence: a case is edited, nobody
re-runs it, and the number everyone quotes belongs to a case that no longer
exists. That is how this repository arrived at an audit — the original suite's
scores were stale or unrunnable and nothing said so.

So every measurement is written down next to the cases, with a fingerprint of
the case it measured:

    plugins/<plugin>/evals/measurements.json

`check_eval_freshness.py` recomputes the fingerprint and reports a case that
has changed since, or was never measured. It compares content rather than
dates, so it works on a shallow CI checkout.

This module is the shared part: the fingerprint, and reading and writing the
ledger.
"""
import hashlib
import json
from pathlib import Path

LEDGER = "measurements.json"

HEADER = (
    "What each case scored when it was last run, and a fingerprint of the "
    "case at that moment. check_eval_freshness.py reports anything edited "
    "since. Written by scripts/run-evals.sh; do not edit by hand."
)


def case_fingerprint(case_dir):
    """A hash of everything that decides what the case measures."""
    digest = hashlib.sha256()
    for path in sorted(Path(case_dir).rglob("*")):
        if not path.is_file():
            continue
        digest.update(path.relative_to(case_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def ledger_path(plugin_dir):
    return Path(plugin_dir) / "evals" / LEDGER


def read_ledger(plugin_dir):
    path = ledger_path(plugin_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    cases = data.get("cases")
    return cases if isinstance(cases, dict) else {}


def write_ledger(plugin_dir, cases):
    path = ledger_path(plugin_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"$comment": HEADER, "cases": dict(sorted(cases.items()))},
                   indent=2) + "\n",
        encoding="utf-8")
    return path
