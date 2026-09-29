#!/usr/bin/env python3
"""Workflow rules that are cheap to keep and expensive to notice missing.

  - a `permissions:` block, so the token is not whatever the repository
    default happens to be
  - `persist-credentials: false` on every checkout, so no token is left in
    .git/config for whatever runs next — and in the eval workflow, what runs
    next is a model with a shell
  - no `${{ ... }}` inside a `run:` block: that is textual substitution into
    the script, which is how an input becomes a command
  - actions and the CLI pinned, so a green run stays reproducible. An action
    is pinned only by a full commit SHA: a tag such as `v4` is a name its
    owner can move to other code, which is how a compromised action reaches
    every workflow that trusted the tag

And, for a step that actually runs Claude unattended, the three that decide
how much it can do while nobody is watching: a turn cap, a tool grant narrower
than "everything", and no permission bypass.

Usage: check_workflows.py [repository root]
Exit 0 when every workflow is clean, 1 otherwise.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPRESSION = re.compile(r"\$\{\{")
RUN_KEY = re.compile(r"^(\s*)-?\s*run:\s*(.*)$")
CHECKOUT = re.compile(r"^(\s*)-\s*uses:\s*actions/checkout@")
NPM_INSTALL = re.compile(r"npm install -g (\S+)")
FLOATING_ACTION = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@(main|master|latest)\b")
# Any other ref that is not a full commit SHA: a tag, or a branch by another
# name. Local actions (./path) and docker:// images have no @ref to check.
ACTION_REF = re.compile(r"uses:\s*([\w.-]+/[\w./-]+)@([^\s#'\"]+)")
FULL_SHA = re.compile(r"[0-9a-f]{40}")

# A step that starts Claude, rather than one that merely mentions it.
RUNS_CLAUDE = re.compile(r"(^|\s)(claude|npx @anthropic-ai/claude-code)\s")
BYPASS = re.compile(
    r"--dangerously-skip-permissions|--permission-mode[= ]\s*bypassPermissions")
# A grant with no pattern after the tool name lets that tool do anything.
BROAD_GRANT = re.compile(
    r"--allow(?:ed)?-tools?[= ]\s*([^\\\n]*)")


def run_blocks(lines):
    """(line number, text) for every line that is part of a run: script."""
    index = 0
    while index < len(lines):
        match = RUN_KEY.match(lines[index])
        if not match:
            index += 1
            continue
        indent, inline = match.group(1), match.group(2).strip()
        if inline and inline not in {"|", ">", "|-", ">-", "|+"}:
            yield index + 1, inline
            index += 1
            continue
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.strip() and (len(line) - len(line.lstrip())) <= len(indent):
                break
            yield index + 1, line
            index += 1


def check_claude_step(script, shown, number, problems):
    """An unattended run is bounded by what the command line says, or not."""
    if not RUNS_CLAUDE.search(script):
        return
    # `plugin eval` is bounded by the suite rather than the command line:
    # every case declares its own max_turns, timeout_seconds and
    # allowed_tools, and the run happens in the eval sandbox. The operator
    # grant it takes is a ceiling for those, not a free hand.
    evaluating = "plugin eval" in script or "plugin validate" in script
    bounded = True if evaluating else "--max-turns" in script
    if not bounded:
        problems.append(
            f"{shown}:{number}: runs Claude with no --max-turns. Nobody is "
            f"watching, and the loop has no upper bound"
        )
    if BYPASS.search(script):
        problems.append(
            f"{shown}:{number}: runs Claude with permissions bypassed. Every "
            f"guard the repository ships is off for that run"
        )
    for match in (() if evaluating else BROAD_GRANT.finditer(script)):
        granted = match.group(1).split("#")[0].strip().strip('"\'')
        bare = [tool for tool in granted.split()
                if tool in {"Bash", "Write", "Edit", "WebFetch"}]
        if bare:
            problems.append(
                f"{shown}:{number}: grants {', '.join(bare)} with no pattern, "
                f"so the run may do anything that tool can. Scope it, e.g. "
                f"Bash(npm test:*)"
            )


def check(path, root, problems):
    shown = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not re.search(r"^permissions:", text, re.M):
        problems.append(
            f"{shown}: no permissions: block — the job runs with whatever the "
            f"repository default grants, which is usually more than it needs"
        )

    for index, line in enumerate(lines):
        match = CHECKOUT.match(line)
        if not match:
            continue
        indent = len(match.group(1))
        block = []
        for following in lines[index + 1:]:
            if following.strip() and (len(following) - len(following.lstrip())) <= indent:
                break
            block.append(following)
        if "persist-credentials: false" not in "\n".join(block):
            problems.append(
                f"{shown}:{index + 1}: checkout without "
                f"persist-credentials: false — the token stays in .git/config "
                f"for everything that runs after it"
            )

    scripts = {}
    for number, line in run_blocks(lines):
        scripts.setdefault(number, []).append(line)
        if EXPRESSION.search(line):
            problems.append(
                f"{shown}:{number}: ${{{{ }}}} inside a run: block. It is "
                f"pasted into the script before the shell sees it; pass it "
                f"through env: instead"
            )

    # Rejoin each run: block and judge it as the one command it is.
    joined, start = [], None
    previous = None
    for number in sorted(scripts):
        if previous is None or number != previous + 1:
            if start is not None:
                check_claude_step("\n".join(joined), shown, start, problems)
            joined, start = [], number
        joined.extend(scripts[number])
        previous = number
    if start is not None:
        check_claude_step("\n".join(joined), shown, start, problems)

    for index, line in enumerate(lines):
        match = FLOATING_ACTION.search(line)
        if match:
            problems.append(
                f"{shown}:{index + 1}: {match.group(1)} is used at "
                f"@{match.group(2)}, which is whatever it holds today"
            )

    for index, line in enumerate(lines):
        match = ACTION_REF.search(line)
        if (match and not FLOATING_ACTION.search(line)
                and not FULL_SHA.fullmatch(match.group(2))):
            problems.append(
                f"{shown}:{index + 1}: {match.group(1)} is pinned to "
                f"@{match.group(2)}, a tag its owner can move; pin the full "
                f"commit SHA and keep the tag as a comment"
            )

    for index, line in enumerate(lines):
        match = NPM_INSTALL.search(line)
        if match and "@" not in match.group(1)[1:]:
            problems.append(
                f"{shown}:{index + 1}: {match.group(1)} is installed unpinned, "
                f"so two runs of the same commit can use different versions"
            )


def main(root=ROOT):
    problems = []
    files = sorted((root / ".github" / "workflows").glob("*.yml"))
    for path in files:
        check(path, root, problems)

    if problems:
        print("Workflow check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK — {len(files)} workflow(s) scoped, pinned and free of "
          f"interpolated shell")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
