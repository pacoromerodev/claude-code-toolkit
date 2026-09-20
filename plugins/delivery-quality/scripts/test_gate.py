#!/usr/bin/env python3
"""Stop hook: run the project's tests before the session is allowed to end.

Opt-in on purpose. The gate runs only when the project asks for it, with any
of these in the project root:

    .claude/test-gate            marker file, runner auto-detected
    .claude/test-gate.sh         executable, run as-is
    .claude/test-gate.json       {"command": [...], "timeout": 600,
                                  "only_when_changed": ["src/**", "pom.xml"]}

Exit 2 stops the session from ending and hands stderr to Claude, which then
has to fix the failures. Any other exit code lets the session end.
"""
import fnmatch
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMEOUT = int(os.environ.get("CLAUDE_TEST_GATE_TIMEOUT", "900"))

RUNNERS = [
    ("pom.xml", ["mvn", "-q", "-B", "test"]),
    ("build.gradle.kts", ["./gradlew", "test", "--console=plain"]),
    ("build.gradle", ["./gradlew", "test", "--console=plain"]),
    ("go.mod", ["go", "test", "./..."]),
    ("Cargo.toml", ["cargo", "test", "--quiet"]),
    ("pyproject.toml", ["pytest", "-q"]),
    ("pytest.ini", ["pytest", "-q"]),
]

# Lines that mean "a test failed", most specific first. Used to surface the
# first real failure instead of the build summary, which on Maven and Gradle
# is the last thing printed and says nothing useful.
FAILURE_MARKERS = (
    "FAILED",
    "FAIL:",
    "AssertionError",
    "[ERROR] Tests run:",
    "Tests run:",
    "expected:",
    "--- FAIL",
    "panic:",
    "assertion failed",
    "● ",
)


def project_root(payload):
    for candidate in (
        os.environ.get("CLAUDE_PROJECT_DIR"),
        payload.get("cwd"),
        os.getcwd(),
    ):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return Path.cwd()


def config(root):
    """The gate's settings, or None when this project has not opted in."""
    claude = root / ".claude"

    settings_file = claude / "test-gate.json"
    if settings_file.is_file():
        try:
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass  # fall through to the simpler forms
        return {}

    if (claude / "test-gate.sh").is_file() or (claude / "test-gate").exists():
        return {}

    return None


def detect(root, settings):
    """The command to run, or None when no runner fits this project."""
    command = settings.get("command")
    if isinstance(command, list) and command:
        return command
    if isinstance(command, str) and command.strip():
        return ["bash", "-lc", command]

    script = root / ".claude" / "test-gate.sh"
    if script.is_file() and os.access(script, os.X_OK):
        return [str(script)]

    package = root / "package.json"
    if package.is_file():
        try:
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
            if "test" in scripts:
                return ["npm", "test", "--silent"]
        except Exception:
            pass

    for marker, runner in RUNNERS:
        if (root / marker).is_file() and (
            shutil.which(runner[0]) or (root / runner[0]).exists()
        ):
            return runner
    return None


def changed_files(root):
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return [line[3:].strip() for line in result.stdout.splitlines() if line[3:].strip()]


def should_run(root, settings):
    """False when nothing the project cares about changed."""
    patterns = settings.get("only_when_changed")
    if not isinstance(patterns, list) or not patterns:
        return True

    changed = changed_files(root)
    if changed is None:
        return True  # cannot tell: run it

    for path in changed:
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern) or path.startswith(
                pattern.rstrip("*").rstrip("/") + "/"
            ):
                return True
    return False


def first_failure(output):
    """The first lines that look like an actual failure, with context."""
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if any(marker in line for marker in FAILURE_MARKERS):
            start = max(0, index - 2)
            return "\n".join(lines[start:index + 18])
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # Never re-enter: without this the gate fires again on the stop that
    # follows its own feedback, and the session cannot end.
    if payload.get("stop_hook_active"):
        return 0

    root = project_root(payload)
    settings = config(root)
    if settings is None:
        return 0

    if not should_run(root, settings):
        return 0

    command = detect(root, settings)
    if command is None:
        print("Test gate is enabled but no test runner was found. Add the "
              "command to .claude/test-gate.json, or write "
              ".claude/test-gate.sh.", file=sys.stderr)
        return 0

    timeout = settings.get("timeout")
    if not isinstance(timeout, int) or timeout <= 0:
        timeout = DEFAULT_TIMEOUT

    printable = " ".join(command)
    try:
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        print(f"Test gate: `{printable}` timed out after {timeout}s. "
              "Find out why the suite hangs before ending the session.",
              file=sys.stderr)
        return 2
    except Exception as error:
        print(f"Test gate could not run `{printable}`: {error}", file=sys.stderr)
        return 0

    if result.returncode == 0:
        return 0

    output = (result.stdout or "") + "\n" + (result.stderr or "")
    detail = first_failure(output)
    if detail is None:
        detail = "\n".join(output.strip().splitlines()[-40:])
        heading = "Last 40 lines of output"
    else:
        heading = "First failure"

    print(
        f"Test gate failed: `{printable}` exited {result.returncode}.\n"
        "Fix the failures below. Do not weaken, skip or delete a test to make "
        "this pass — if a test is wrong, say so and explain why.\n\n"
        f"{heading}:\n{detail}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
