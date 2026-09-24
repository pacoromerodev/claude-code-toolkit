#!/usr/bin/env python3
"""Record which component fired, and which prompts fired nothing.

An eval answers "does this skill help", and costs a session per case to do
it. It also answers a smaller question on the way — did the skill fire at all
— and that one is observable for free, from ordinary use.

Two hooks feed one log: `UserPromptSubmit` records the prompt, `PreToolUse`
on `Skill` and `Task` records what the model reached for. A prompt with
nothing after it is the interesting row: a situation the toolkit claims and
did not answer.

Opt in per project, because this writes down what you type:

    mkdir -p .claude && touch .claude/routing-log

The log lives outside the repository, under the plugin's data directory, and
the prompt is truncated. Nothing is sent anywhere.

Reading it back: `routing_report.py`.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

MARKER = "routing-log"
PROMPT_MAX = 200
# Enough to see the shape of a week's work; past that the oldest rows go.
MAX_LINES = 5000


def data_dir():
    """Where the log goes: never the repository being worked in."""
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    if base:
        return Path(base)
    return Path.home() / ".claude" / "plugins" / "data" / "skill-forge"


def project_root(payload):
    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    return Path(cwd)


def enabled(root):
    return (root / ".claude" / MARKER).exists()


def entry(payload):
    """One row, or None when the event says nothing about routing."""
    event = payload.get("hook_event_name")
    session = (payload.get("session_id") or "")[:8]
    stamp = datetime.now().isoformat(timespec="seconds")

    if event == "UserPromptSubmit":
        prompt = " ".join((payload.get("prompt") or "").split())
        if not prompt:
            return None
        return {"at": stamp, "session": session, "prompt": prompt[:PROMPT_MAX]}

    if event == "PreToolUse":
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return None
        name = tool_input.get("skill") or tool_input.get("subagent_type")
        if not name:
            return None
        kind = "skill" if payload.get("tool_name") == "Skill" else "agent"
        return {"at": stamp, "session": session, "fired": str(name), "kind": kind}

    return None


def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")

    # Keep it bounded without a second tool: rewrite only when it has grown
    # past the cap, which is rare.
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > MAX_LINES:
        path.write_text("\n".join(lines[-MAX_LINES:]) + "\n", encoding="utf-8")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    if not enabled(project_root(payload)):
        return 0

    row = entry(payload)
    if row is None:
        return 0

    append(data_dir() / "routing.jsonl", row)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # A hook that breaks must never take the session with it.
        sys.exit(0)
