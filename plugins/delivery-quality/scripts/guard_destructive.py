#!/usr/bin/env python3
"""PreToolUse guard: block commands that destroy work you cannot get back.

The test is not "is this dangerous" — most useful commands are. It is whether
the damage survives the session: a force-push that rewrites shared history, a
reset that discards uncommitted work, a delete outside the project, a DROP
against something that is not a test database.

Exit 2 blocks and hands stderr to Claude. Anything else lets the call through,
including every unexpected error: a broken guard must not brick a session.

Projects can relax this in `.claude/destructive-guard-allow`, one regular
expression per line, matched against the whole command.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master", "develop", "release", "production"}


def project_root(payload):
    for candidate in (
        os.environ.get("CLAUDE_PROJECT_DIR"),
        payload.get("cwd"),
        os.getcwd(),
    ):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    return Path.cwd().resolve()


def allowlist(root):
    path = root / ".claude" / "destructive-guard-allow"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    rules = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                rules.append(re.compile(line))
            except re.error:
                continue
    return rules


def git(root, *args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def outside_project(target, root):
    """True when this path resolves outside the project directory."""
    target = target.strip("\"'")
    if target.startswith("~") or target in {"/", "/*"}:
        return True
    try:
        resolved = (root / target).resolve() if not target.startswith("/") \
            else Path(target).resolve()
    except Exception:
        return True
    return root != resolved and root not in resolved.parents


def check_rm(command, root):
    match = re.search(r"\brm\s+((?:-\S+\s+)*)(.+)", command)
    if not match:
        return None
    flags = match.group(1)
    if "r" not in flags.replace("--", "") and "-rf" not in flags:
        return None

    for target in re.findall(r"[^\s;&|]+", match.group(2)):
        if target.startswith("-"):
            continue
        if outside_project(target, root):
            return (
                f"`rm -r {target}` deletes outside the project directory "
                f"({root}).\n"
                "If that is really the intent, run it yourself — an agent "
                "should not reach past the project it was given."
            )
    return None


def check_git(command, root):
    if re.search(r"\bgit\s+push\b.*(--force\b|--force-with-lease=?\s|-f\b)", command):
        if "--force-with-lease" in command:
            return None  # refuses to clobber work it has not seen: acceptable
        branch = None
        match = re.search(r"\bgit\s+push\s+\S+\s+(?:\S+:)?(\S+)", command)
        if match:
            branch = match.group(1).lstrip("+")
        else:
            branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        if branch in PROTECTED_BRANCHES:
            return (
                f"`git push --force` to {branch} rewrites history other people "
                f"have already pulled.\n"
                "Use --force-with-lease, push to a feature branch, or do this "
                "yourself after telling the team."
            )

    if re.search(r"\bgit\s+reset\s+.*--hard\b", command):
        dirty = git(root, "status", "--porcelain")
        if dirty:
            count = len(dirty.splitlines())
            return (
                f"`git reset --hard` discards {count} uncommitted change(s), "
                f"unrecoverably.\n"
                "Commit them, stash them, or say explicitly that they are "
                "meant to be thrown away."
            )

    if re.search(r"\bgit\s+clean\s+.*-\w*[dfx]", command):
        return (
            "`git clean` deletes untracked files with no way back — including "
            "local config and scratch work that was never meant to be "
            "committed.\n"
            "Run `git clean -n` first and check what it would remove."
        )

    if re.search(r"\bgit\s+branch\s+-D\b", command):
        return (
            "`git branch -D` force-deletes a branch even when it is unmerged.\n"
            "Use -d, which refuses when there are unmerged commits."
        )

    if re.search(r"\bgit\s+(checkout|restore)\s+.*(--|\.)\s*$", command):
        dirty = git(root, "status", "--porcelain")
        if dirty:
            return (
                "This discards every uncommitted change in the working tree.\n"
                "Stash them first if any of it should survive."
            )
    return None


def check_sql(command):
    match = re.search(
        r"\b(DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE"
        r"|DELETE\s+FROM\s+\S+\s*(?:;|$))",
        command,
        re.I,
    )
    if not match:
        return None
    # No word boundaries: the marker is usually glued to something else —
    # app_test, localhost, dev-cluster — and \btest\b misses every one.
    if re.search(r"(test|dev|local|fixture|sandbox|staging|tmp)", command, re.I):
        return None
    return (
        f"`{match.group(1).strip()}` against what does not look like a test "
        f"database.\n"
        "Name the database explicitly if it is a local or test one, or run "
        "this yourself against production."
    )


def check_misc(command):
    if re.search(r"\b(mkfs|dd\s+if=\S+\s+of=/dev/)", command):
        return "This writes directly to a block device. Run it yourself."
    if re.search(r"\bchmod\s+(-R\s+)?777\b", command):
        return (
            "`chmod 777` makes the target world-writable.\n"
            "Grant the narrowest mode that works instead."
        )
    if re.search(r"\bkubectl\s+delete\b.*\b(--all|namespace)\b", command) and \
       not re.search(r"(test|dev|local|sandbox|staging)", command, re.I):
        return (
            "This deletes Kubernetes resources in bulk outside an obviously "
            "non-production context.\n"
            "Name the namespace, or run it yourself."
        )
    if re.search(r"\bterraform\s+(destroy|apply)\b", command) and \
       "-auto-approve" in command:
        return (
            "`terraform` with -auto-approve applies infrastructure changes "
            "with no plan review.\n"
            "Run the plan, read it, then apply without the flag."
        )
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    root = project_root(payload)

    if any(rule.search(command) for rule in allowlist(root)):
        return 0

    for check in (
        lambda: check_rm(command, root),
        lambda: check_git(command, root),
        lambda: check_sql(command),
        lambda: check_misc(command),
    ):
        reason = check()
        if reason:
            print(f"Blocked: {reason}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
