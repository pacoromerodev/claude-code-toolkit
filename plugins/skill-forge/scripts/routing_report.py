#!/usr/bin/env python3
"""Read the routing log and say what fired, and what fired nothing.

    python3 routing_report.py                 # the default log
    python3 routing_report.py path/to.jsonl   # a specific one

Two questions, from the same rows:

  - **What fires, and how often.** A component nobody reaches is context
    spent on a description nothing matches.
  - **Which prompts fired nothing.** This is the half an eval cannot see: a
    case measures a prompt somebody wrote for it, while this is the prompt
    somebody actually typed. A run of these in one domain is a description
    that does not claim the situation it was written for.

It says nothing about whether firing helped. That needs the two arms of an
eval, and no log can answer it.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path


def default_log():
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    root = Path(base) if base else Path.home() / ".claude" / "plugins" / "data" / "skill-forge"
    return root / "routing.jsonl"


def read(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def turns(rows):
    """(prompt row, [fired rows]) per turn, matched within a session."""
    open_turn = {}
    result = []
    for row in rows:
        session = row.get("session", "")
        if "prompt" in row:
            if session in open_turn:
                result.append(open_turn[session])
            open_turn[session] = (row, [])
        elif "fired" in row and session in open_turn:
            open_turn[session][1].append(row)
    result.extend(open_turn.values())
    return result


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else default_log()
    if not path.is_file():
        print(f"No routing log at {path}.")
        print("Enable it per project: mkdir -p .claude && touch .claude/routing-log")
        return 0

    rows = read(path)
    conversations = turns(rows)
    fired = Counter(row["fired"] for _, entries in conversations for row in entries)
    silent = [prompt for prompt, entries in conversations if not entries]

    print(f"{len(conversations)} prompt(s) recorded in {path}\n")

    if fired:
        width = max(len(name) for name in fired)
        print("What fired")
        for name, count in fired.most_common():
            print(f"  {name:<{width}}  {count}")
    else:
        print("Nothing fired in any recorded turn.")

    print(f"\nPrompts that fired nothing: {len(silent)} of {len(conversations)}")
    for row in silent[-15:]:
        print(f"  {row.get('at', '')}  {row.get('prompt', '')}")
    if len(silent) > 15:
        print(f"  … and {len(silent) - 15} earlier")

    print("\nA prompt firing nothing is not a fault on its own — most prompts")
    print("should fire nothing. Read these for a situation a component claims")
    print("and did not answer; that is a description to rewrite, and")
    print("skill-describer is what rewrites it.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(130)
