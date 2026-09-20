#!/usr/bin/env python3
"""PostCompact / SessionStart hook: hand back the state the snapshot captured.

Runs on two events, for two different losses:

  PostCompact  — the conversation was summarised. The summary keeps the
                 narrative and drops the particulars.
  SessionStart — the session is new or resumed. Nothing carried over at all.

Emits `hookSpecificOutput.additionalContext`, which is injected into the
model's context. Prints nothing when there is no snapshot, so a fresh session
in a repo that never compacted stays silent.

Always exits 0.
"""
import json
import os
import sys
import time
from pathlib import Path

# Older than this and the snapshot describes a tree that has since moved on.
MAX_AGE_HOURS = 24


def project_root(payload):
    for candidate in (
        os.environ.get("CLAUDE_PROJECT_DIR"),
        payload.get("cwd"),
        os.getcwd(),
    ):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return Path.cwd()


def snapshot_for(root, session):
    directory = root / ".claude" / "state"
    if not directory.is_dir():
        return None

    exact = directory / f"{session}.md"
    if exact.is_file():
        return exact

    # A resumed session gets a new id, so fall back to the most recent
    # snapshot in this project.
    candidates = sorted(
        (p for p in directory.glob("*.md") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def prune(root, keep):
    """Snapshots from sessions long finished are noise. Drop them."""
    directory = root / ".claude" / "state"
    cutoff = time.time() - MAX_AGE_HOURS * 3600 * 7
    for path in directory.glob("*.md"):
        try:
            if path != keep and path.stat().st_mtime < cutoff:
                path.unlink()
        except Exception:
            continue


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    root = project_root(payload)
    session = str(payload.get("session_id") or "session").replace("/", "_")[:64]

    path = snapshot_for(root, session)
    if path is None:
        return 0

    try:
        age_hours = (time.time() - path.stat().st_mtime) / 3600
        body = path.read_text(encoding="utf-8").strip()
    except Exception:
        return 0

    if not body:
        return 0

    if age_hours > MAX_AGE_HOURS:
        # Stale enough that presenting it as current would be worse than
        # silence, but worth one line in case it is still wanted.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": payload.get("hook_event_name", "SessionStart"),
                "additionalContext": (
                    f"A saved working-tree snapshot exists at "
                    f"`{path.relative_to(root)}` but it is {int(age_hours)} "
                    f"hours old, so it is not being restored. Read it only if "
                    f"the user refers to earlier work in this repo."
                ),
            },
            "suppressOutput": True,
        }))
        return 0

    prune(root, path)

    header = (
        "State restored after compaction. The conversation above was "
        "summarised; what follows was measured from the working tree before "
        "that happened. Verify anything you act on — the tree may have moved "
        "since.\n\n"
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": payload.get("hook_event_name", "PostCompact"),
            "additionalContext": header + body,
        },
        "suppressOutput": True,
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
