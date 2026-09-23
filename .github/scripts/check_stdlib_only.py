#!/usr/bin/env python3
"""Hook scripts must import nothing outside the standard library.

A hook runs on someone else's machine, inside their session, before they have
installed anything. The first import error disables the hook — and a guard that
silently stops guarding is worse than no guard at all. So this is a hard rule,
enforced here rather than left to review.

"The standard library" is not one library: it depends on the version. The
floor is declared here, once, and this script holds two things to it — the
modules the hooks import, and the version matrix in the workflow that tests
them. A module added after the floor passes an import check on the runner and
fails on the machine the hook actually runs on.

Usage: check_stdlib_only.py [repository root]
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The oldest Python these hooks must run on. 3.8 rather than something newer
# because a hook uses whatever `python3` is already on the machine: a stock
# macOS still answers 3.9, and nothing about a guard script needs more.
MINIMUM = (3, 8)

# Standard library, but only from this version on.
ADDED_IN = {
    "tomllib": (3, 11),
    "zoneinfo": (3, 9),
    "graphlib": (3, 9),
}

WORKFLOW = "validate.yml"
MATRIX = re.compile(r"python-version:\s*\[(.*?)\]")

# Standard library modules a hook has any business importing. Deliberately
# short: widen it on purpose, not by accident.
ALLOWED = {
    "argparse", "ast", "base64", "collections", "configparser", "contextlib",
    "csv", "dataclasses", "datetime", "difflib", "enum", "fnmatch",
    "functools", "glob", "hashlib", "io", "itertools", "json", "logging",
    "math", "os", "pathlib", "platform", "random", "re", "shlex", "shutil",
    "signal", "socket", "stat", "string", "subprocess", "sys", "tempfile",
    "textwrap", "time", "traceback", "typing", "unicodedata",
    "urllib", "uuid", "warnings", "xml", "zipfile",
}


def imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import: within the plugin, fine
                continue
            if node.module:
                yield node.module.split(".")[0], node.lineno


def check_matrix(root, problems):
    """The workflow must actually test the version this file calls the floor."""
    workflow = root / ".github" / "workflows" / WORKFLOW
    if not workflow.is_file():
        return
    match = MATRIX.search(workflow.read_text(encoding="utf-8"))
    if not match:
        problems.append(
            f".github/workflows/{WORKFLOW}: no python-version matrix, so "
            f"nothing tests the {'.'.join(map(str, MINIMUM))} floor"
        )
        return
    tested = []
    for raw in match.group(1).split(","):
        raw = raw.strip().strip("\"'")
        try:
            tested.append(tuple(int(part) for part in raw.split(".")))
        except ValueError:
            continue
    if tested and min(tested) != MINIMUM:
        floor = ".".join(map(str, MINIMUM))
        lowest = ".".join(map(str, min(tested)))
        problems.append(
            f".github/workflows/{WORKFLOW}: the matrix starts at {lowest}, "
            f"this script's floor is {floor}. One of the two is wrong, and "
            f"whichever it is, some hook is untested on the version it will "
            f"meet"
        )


def main(root=ROOT):
    problems = []
    checked = 0

    check_matrix(root, problems)

    for script in sorted(root.glob("plugins/*/scripts/*.py")):
        checked += 1
        rel = script.relative_to(root).as_posix()
        try:
            tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except SyntaxError as error:
            problems.append(f"{rel}:{error.lineno}: syntax error: {error.msg}")
            continue

        for module, line in imported_modules(tree):
            if module in ADDED_IN:
                problems.append(
                    f"{rel}:{line}: imports {module!r}, which arrived in "
                    f"Python {'.'.join(map(str, ADDED_IN[module]))}. These "
                    f"scripts run on {'.'.join(map(str, MINIMUM))}"
                )
            elif module not in ALLOWED:
                problems.append(
                    f"{rel}:{line}: imports {module!r}, which is not in the "
                    f"allowed standard-library set"
                )

    if problems:
        print("Dependency check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nHooks must run on a machine where nothing has been installed. "
            "Rewrite using the standard library, or widen ALLOWED in this "
            "script deliberately."
        )
        return 1

    print(f"OK — {checked} hook script(s) use only the standard library")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
