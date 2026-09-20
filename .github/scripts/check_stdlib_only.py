#!/usr/bin/env python3
"""Hook scripts must import nothing outside the standard library.

A hook runs on someone else's machine, inside their session, before they have
installed anything. The first import error disables the hook — and a guard that
silently stops guarding is worse than no guard at all. So this is a hard rule,
enforced here rather than left to review.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Standard library modules a hook has any business importing. Deliberately
# short: widen it on purpose, not by accident.
ALLOWED = {
    "argparse", "ast", "base64", "collections", "configparser", "contextlib",
    "csv", "dataclasses", "datetime", "difflib", "enum", "fnmatch",
    "functools", "glob", "hashlib", "io", "itertools", "json", "logging",
    "math", "os", "pathlib", "platform", "random", "re", "shlex", "shutil",
    "signal", "socket", "stat", "string", "subprocess", "sys", "tempfile",
    "textwrap", "time", "tomllib", "traceback", "typing", "unicodedata",
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


def main():
    problems = []
    checked = 0

    for script in sorted(ROOT.glob("plugins/*/scripts/*.py")):
        checked += 1
        rel = script.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except SyntaxError as error:
            problems.append(f"{rel}:{error.lineno}: syntax error: {error.msg}")
            continue

        for module, line in imported_modules(tree):
            if module not in ALLOWED:
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
    sys.exit(main())
