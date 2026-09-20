#!/usr/bin/env python3
"""PreCompact hook: snapshot the facts compaction is about to blur.

Compaction summarises the conversation, and a summary is lossy in a specific
way — it keeps the narrative and drops the particulars. Which branch. Which
files are half-edited. What the last commit actually was.

None of that needs to be remembered, because it can be measured. This writes
the measurement to .claude/state/<session>.md so restore_state.py can hand it
back afterwards.

Always exits 0. Failing to take a snapshot must never interrupt a compaction.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_FILES = 40
MAX_DIFF_LINES = 60


def project_root(payload):
    for candidate in (
        os.environ.get("CLAUDE_PROJECT_DIR"),
        payload.get("cwd"),
        os.getcwd(),
    ):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return Path.cwd()


def git(root, *args, timeout=8):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def clip(lines, limit, what):
    if len(lines) <= limit:
        return lines
    return lines[:limit] + [f"... and {len(lines) - limit} more {what}"]


def build(root, payload):
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    trigger = payload.get("trigger") or payload.get("matcher") or "compaction"

    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD") or "(not a git repo)"
    status = [line for line in git(root, "status", "--porcelain").splitlines() if line]
    diffstat = git(root, "diff", "HEAD", "--stat")
    staged = git(root, "diff", "--cached", "--name-only")
    commits = git(root, "log", "--oneline", "-5")
    stashes = git(root, "stash", "list")

    parts = [
        "# Session state",
        "",
        f"Snapshot taken before {trigger} compaction, {when}.",
        "These are measured facts about the working tree, not a summary of the",
        "conversation — check them against reality before relying on them.",
        "",
        f"**Branch:** `{branch}`",
        "",
    ]

    if status:
        parts.append(f"**Uncommitted changes ({len(status)} file(s)):**")
        parts.append("")
        parts.append("```")
        parts.extend(clip(status, MAX_FILES, "files"))
        parts.append("```")
        parts.append("")
    else:
        parts.append("**Working tree is clean.**")
        parts.append("")

    if staged:
        parts.append("**Staged:**")
        parts.append("")
        parts.append("```")
        parts.extend(clip(staged.splitlines(), MAX_FILES, "files"))
        parts.append("```")
        parts.append("")

    if diffstat:
        parts.append("**Diff against HEAD:**")
        parts.append("")
        parts.append("```")
        parts.extend(clip(diffstat.splitlines(), MAX_DIFF_LINES, "lines"))
        parts.append("```")
        parts.append("")

    if commits:
        parts.append("**Last commits:**")
        parts.append("")
        parts.append("```")
        parts.extend(commits.splitlines())
        parts.append("```")
        parts.append("")

    if stashes:
        parts.append("**Stashes:** " + str(len(stashes.splitlines())) +
                     " — check whether any belong to this session.")
        parts.append("")

    # A handoff note written by /handoff outranks anything measured, because a
    # person wrote it on purpose.
    handoff = root / ".claude" / "handoff.md"
    if handoff.is_file():
        try:
            text = handoff.read_text(encoding="utf-8").strip()
            if text:
                parts.append("**Handoff note (written deliberately, trust this "
                             "over the rest):**")
                parts.append("")
                parts.extend(text.splitlines()[:60])
                parts.append("")
        except Exception:
            pass

    return "\n".join(parts).rstrip() + "\n"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    root = project_root(payload)
    session = str(payload.get("session_id") or "session").replace("/", "_")[:64]

    directory = root / ".claude" / "state"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        # Namespaced by session: two sessions in the same repo must not
        # overwrite each other's snapshot.
        (directory / f"{session}.md").write_text(build(root, payload), encoding="utf-8")
    except Exception:
        return 0

    print(json.dumps({
        "systemMessage": "Working-tree state saved; it will be restored after "
                         "compaction.",
        "suppressOutput": True,
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
