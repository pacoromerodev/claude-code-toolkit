#!/usr/bin/env python3
"""Workflow rules that are cheap to keep and expensive to notice missing.

  - a `permissions:` block, so the token is not whatever the repository
    default happens to be
  - `persist-credentials: false` on every checkout, so no token is left in
    .git/config for whatever runs next — and in the eval workflow, what runs
    next is a model with a shell
  - no `${{ ... }}` inside a `run:` block: that is textual substitution into
    the script, which is how an input becomes a command
  - actions and the CLI pinned, so a green run stays reproducible

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

    for number, line in run_blocks(lines):
        if EXPRESSION.search(line):
            problems.append(
                f"{shown}:{number}: ${{{{ }}}} inside a run: block. It is "
                f"pasted into the script before the shell sees it; pass it "
                f"through env: instead"
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
