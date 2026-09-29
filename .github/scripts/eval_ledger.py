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

A case is only half of what a number measures; the other half is the
component it exercises. `/review-diff` once changed while its case did not,
and the old score still read as current. So each entry also carries a
`components` fingerprint: the files of whatever the case names in its
`tags:`, resolved against the plugin. A case tagged `negative` measures that
nothing fires, so it depends on every skill, agent and command description.

This module is the shared part: the fingerprint, and reading and writing the
ledger.
"""
import hashlib
import json
import re
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


TAGS = re.compile(r"^tags:\s*\[(.*)\]\s*$", re.MULTILINE)
KINDS = ("skills", "agents", "commands")


def case_tags(case_dir):
    """The names in a case's `tags: [...]` line; empty when there is none."""
    path = Path(case_dir) / "case.yaml"
    if not path.is_file():
        return []
    match = TAGS.search(path.read_text(encoding="utf-8"))
    if not match:
        return []
    return [t.strip().strip("'\"") for t in match.group(1).split(",") if t.strip()]


def component_files(plugin_dir, case_dir):
    """Every file of the components the case exercises, relative to the plugin."""
    plugin_dir = Path(plugin_dir)
    tags = case_tags(case_dir)
    found = set()

    def add(path):
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            found.update(f for f in path.rglob("*") if f.is_file())

    if "negative" in tags:
        for kind in KINDS:
            add(plugin_dir / kind)
    for tag in tags:
        add(plugin_dir / "skills" / tag)
        add(plugin_dir / "agents" / f"{tag}.md")
        add(plugin_dir / "commands" / f"{tag}.md")
        script = plugin_dir / "scripts" / f"{tag}.py"
        if script.is_file():
            add(script)
            add(plugin_dir / "hooks" / "hooks.json")
    return sorted(p.relative_to(plugin_dir) for p in found)


def component_fingerprint(plugin_dir, case_dir):
    """A hash of the component files; None when the tags name none."""
    files = component_files(plugin_dir, case_dir)
    if not files:
        return None
    digest = hashlib.sha256()
    for relative in files:
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update((Path(plugin_dir) / relative).read_bytes())
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
