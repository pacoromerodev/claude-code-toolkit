#!/usr/bin/env python3
"""SessionStart(compact) hook: hand back the state the snapshot captured.

Compaction summarises the conversation and the particulars go with it. This
reads the snapshot PreCompact wrote and returns it through
`hookSpecificOutput.additionalContext`.

It only ever restores the snapshot this session wrote, and only after a
compaction. A snapshot from another session describes another tree, and a file
found inside a repository could have been committed by anyone: neither is a
measurement of what just happened here.

PostCompact is deliberately not used. It receives the summary but has no way to
add context, so anything it returns is discarded — the course says to
re-inject with SessionStart and a `compact` matcher, and the hooks reference
lists PostCompact under "no decision control".

Always exits 0. Prints nothing when there is no snapshot for this session.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_AGE_HOURS = 24
MAX_CHARACTERS = 8000  # Claude Code caps additionalContext at 10,000
MAX_HANDOFF_LINES = 60
MAX_HANDOFF_CHARACTERS = 2000
MAX_NOTE_AGE_DAYS = 7
MAX_LINE = 200


def git(root, *args, timeout=5):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def working_directory(payload):
    for candidate in (payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    return Path.cwd().resolve()


def project_root(payload):
    cwd = working_directory(payload)
    top = git(cwd, "rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else cwd


def state_dir(root):
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not base:
        base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
        base = str(Path(base) / "claude-code-toolkit" / "context-discipline")
    key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return Path(base) / "state" / f"{root.name}-{key}"


def prune(directory, keep):
    """Snapshots from sessions long finished are noise. Drop them."""
    cutoff = time.time() - 7 * 24 * 3600
    for path in directory.glob("*.md"):
        try:
            if path != keep and path.stat().st_mtime < cutoff:
                path.unlink()
        except Exception:
            continue


def truncate(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit - 60].rstrip() + "\n\n… snapshot truncated here.\n"


def handoff_note(root):
    """The project's live handoff note, if there is a recent one.

    It is read from disk at restore time, not frozen into the snapshot, so
    the note the user has now is the note that comes back. /handoff has the
    assistant write this file, so it is labelled as such: it holds reasoning
    git cannot show, not a measurement.
    """
    path = root / ".claude" / "handoff.md"
    try:
        stat = path.stat()
        if time.time() - stat.st_mtime > MAX_NOTE_AGE_DAYS * 24 * 3600:
            return None
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not text:
        return None
    written = datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [line[:MAX_LINE] for line in text.splitlines()[:MAX_HANDOFF_LINES]]
    note = truncate("\n".join(lines), MAX_HANDOFF_CHARACTERS)
    return (f"**Handoff note** (written by the assistant with /handoff, "
            f"{written}; reasoning git cannot show, check it against the tree):\n\n"
            + note)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    # Only after a compaction, and only for the session that was compacted.
    if payload.get("source") != "compact":
        return 0
    session = str(payload.get("session_id") or "").replace("/", "_")[:64]
    if not session:
        return 0

    root = project_root(payload)
    directory = state_dir(root)
    path = directory / f"{session}.md"
    try:
        stat = path.stat()
        body = path.read_text(encoding="utf-8").strip()
    except Exception:
        return 0
    if not body:
        return 0

    age_hours = (time.time() - stat.st_mtime) / 3600
    if age_hours > MAX_AGE_HOURS:
        return 0

    prune(directory, path)

    note = handoff_note(root)
    header = (
        "Working-tree snapshot from this session, taken just before the "
        "compaction above. The conversation was summarised; these facts were "
        "measured before that. The tree may have moved since, so check "
        "anything you act on.\n\n"
    )
    context = header + (note + "\n\n" if note else "") + body

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": payload.get("hook_event_name", "SessionStart"),
            "additionalContext": truncate(context, MAX_CHARACTERS),
        },
        "suppressOutput": True,
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
