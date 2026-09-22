#!/usr/bin/env python3
"""PreCompact hook: snapshot the facts compaction is about to blur.

Compaction summarises the conversation, and a summary is lossy in a specific
way — it keeps the narrative and drops the particulars. Which branch. Which
files are half-edited. What the last commit actually was.

None of that needs to be remembered, because it can be measured. This writes
the measurement so restore_state.py can hand it back afterwards.

The snapshot is written to the plugin's own data directory, keyed by the
repository, never inside the repository: a file in a working tree gets
committed, cloned, and read back as if this session had produced it.

Always exits 0. Failing to take a snapshot must never interrupt a compaction.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_FILES = 40
MAX_DIFF_LINES = 60
MAX_HANDOFF_LINES = 60


def git(root, *args, timeout=8):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def working_directory(payload):
    """Where Claude is now: the payload's cwd follows it into worktrees and
    after cd, while CLAUDE_PROJECT_DIR stays where the session started."""
    for candidate in (payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    return Path.cwd().resolve()


def project_root(payload):
    """The repository containing the working directory, or the directory."""
    cwd = working_directory(payload)
    top = git(cwd, "rev-parse", "--show-toplevel", timeout=5)
    return Path(top).resolve() if top else cwd


def state_dir(root):
    """Outside the repository: the plugin's data directory, per repository."""
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not base:
        base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
        base = str(Path(base) / "claude-code-toolkit" / "context-discipline")
    key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return Path(base) / "state" / f"{root.name}-{key}"


def clip(lines, limit, what):
    if len(lines) <= limit:
        return lines
    return lines[:limit] + [f"... and {len(lines) - limit} more {what}"]


def build(root, payload):
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    trigger = payload.get("trigger") or "an automatic"

    inside = git(root, "rev-parse", "--is-inside-work-tree")
    parts = [
        "# Working-tree snapshot",
        "",
        f"Taken before {trigger} compaction, {when}, in this session.",
        "These are measured facts about the working tree, not a summary of the",
        "conversation — check them against reality before relying on them.",
        "",
    ]

    if inside != "true":
        parts += [f"**{root}** is not a git repository, so there is nothing to measure.", ""]
        return "\n".join(parts).rstrip() + "\n"

    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    status = [line for line in (git(root, "status", "--porcelain") or "").splitlines() if line]
    diffstat = git(root, "diff", "HEAD", "--stat")
    staged = git(root, "diff", "--cached", "--name-only")
    commits = git(root, "log", "--oneline", "-5")
    stashes = git(root, "stash", "list")

    parts.append(f"**Repository:** `{root}`")
    parts.append(f"**Branch:** `{branch or 'unknown'}`")
    parts.append("")

    if status:
        parts.append(f"**Uncommitted changes ({len(status)} file(s)):**")
        parts.append("")
        parts.append("```")
        parts.extend(clip(status, MAX_FILES, "files"))
        parts.append("```")
        parts.append("")
    else:
        parts.append("**No uncommitted changes.**")
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

    return "\n".join(parts).rstrip() + "\n"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return 0

    root = project_root(payload)
    session = str(payload.get("session_id") or "").replace("/", "_")[:64]
    if not session:
        # Without a session id a snapshot cannot be handed back to the session
        # that produced it, and writing one would only leave a stray file.
        return 0

    directory = state_dir(root)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{session}.md").write_text(build(root, payload), encoding="utf-8")
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
