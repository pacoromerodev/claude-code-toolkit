#!/usr/bin/env python3
"""Stop hook: run the project's tests before Claude ends the turn.

Opt-in on purpose. The gate runs only when the project asks for it, with any
of these in the project root:

    .claude/test-gate            marker file, runner auto-detected
    .claude/test-gate.sh         executable, run as-is
    .claude/test-gate.json       {"command": [...], "timeout": 600,
                                  "only_when_changed": ["src/**", "pom.xml"]}

Stop fires at the end of every turn, not only when the session ends.

A failing suite comes back as `hookSpecificOutput.additionalContext`, which
keeps the conversation going so Claude can fix it, shown as hook feedback
rather than a hook error.

The gate always re-runs on its own re-entry — the run after a failure is what
checks the fix — but it blocks only once. When `stop_hook_active` says this
stop already followed a block and the suite is still red, the turn is allowed
to end and the user is told through `systemMessage`. Blocking again traps a
turn whose right answer is a report: asked to verify rather than to fix,
Claude has to be able to hand back a failing result instead of negotiating
with the user about the hook.

Anything unexpected exits 0 and lets the turn end: a broken gate must not
trap a session.
"""
import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMEOUT = 900
# hooks.json gives this hook 960s. A longer timeout here would be cut off by
# the harness, and the feedback below would never be printed.
TIMEOUT_CEILING = 940
MAX_LINE = 300
MAX_DETAIL = 4000

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


def git(root, *args, timeout=10):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


def working_directory(payload):
    """The payload's cwd follows Claude into worktrees and after cd;
    CLAUDE_PROJECT_DIR stays where the session started."""
    for candidate in (payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    return Path.cwd().resolve()


def project_root(payload):
    cwd = working_directory(payload)
    top = git(cwd, "rev-parse", "--show-toplevel", timeout=5)
    return Path(top.strip()).resolve() if top and top.strip() else cwd


def config(root):
    """The gate's settings, or None when this project has not opted in."""
    claude = root / ".claude"

    settings_file = claude / "test-gate.json"
    if settings_file.is_file():
        try:
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return {"_error": "test-gate.json does not hold an object"}
        except Exception as error:
            return {"_error": f"test-gate.json is not valid JSON: {error}"}

    if (claude / "test-gate.sh").is_file() or (claude / "test-gate").exists():
        return {}

    return None


def detect(root, settings):
    """The command to run, or None when no runner fits this project."""
    command = settings.get("command")
    if isinstance(command, list) and command and all(isinstance(c, str) for c in command):
        return command
    if isinstance(command, str) and command.strip():
        return ["bash", "-lc", command]
    if command is not None:
        return None  # a command of the wrong shape: reported, not ignored

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
    """Files changed in the working tree, plus those committed on this branch
    but not yet on its upstream. A commit made mid-session is still a change
    this session has to answer for."""
    status = git(root, "status", "--porcelain")
    if status is None:
        return None
    changed = {line[3:].strip() for line in status.splitlines() if line[3:].strip()}

    base = None
    upstream = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", timeout=5)
    if upstream and upstream.strip():
        base = upstream.strip()
    else:
        for candidate in ("origin/HEAD", "origin/main", "origin/master"):
            if git(root, "rev-parse", "--verify", "--quiet", candidate, timeout=5):
                base = candidate
                break
    if base:
        committed = git(root, "diff", "--name-only", f"{base}...HEAD", timeout=10)
        if committed:
            changed.update(line.strip() for line in committed.splitlines() if line.strip())
    return sorted(changed)


def should_run(root, settings):
    """False when nothing the project cares about changed."""
    patterns = settings.get("only_when_changed")
    if not isinstance(patterns, list) or not patterns:
        return True
    patterns = [p for p in patterns if isinstance(p, str)]

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


def bounded(text):
    """Clip long lines and the whole block: this goes into the context."""
    lines = [line[:MAX_LINE] for line in text.splitlines()]
    block = "\n".join(lines)
    if len(block) > MAX_DETAIL:
        block = block[:MAX_DETAIL] + "\n… output truncated."
    return block


def effective_timeout(settings):
    """Seconds to allow, never more than the harness gives this hook.

    A project timeout above the hook's own would be cut off by Claude Code
    first, and the feedback below would never reach anyone. The environment
    override is parsed here, not at import time: a value like "15m" must not
    take the hook down with a traceback.
    """
    timeout = settings.get("timeout")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        env_timeout = os.environ.get("CLAUDE_TEST_GATE_TIMEOUT", "")
        timeout = int(env_timeout) if env_timeout.isdigit() and int(env_timeout) > 0 \
            else DEFAULT_TIMEOUT
    return min(timeout, TIMEOUT_CEILING)


def say(message, keep_going):
    """Hook feedback: additionalContext continues the turn, systemMessage is
    for the user only."""
    if keep_going:
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": message},
        }))
    else:
        print(json.dumps({"systemMessage": message}))
    return 0


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return 0

    # True when this stop is itself the result of a previous block by this
    # hook. The tests still run; what changes is that a second block is not
    # allowed. See the module docstring.
    reentry = bool(payload.get("stop_hook_active"))

    root = project_root(payload)
    settings = config(root)
    if settings is None:
        return 0

    if settings.get("_error"):
        return say(f"Test gate: {settings['_error']}. This turn ended without "
                   "tests. Fix .claude/test-gate.json.", keep_going=False)

    if not should_run(root, settings):
        return 0

    command = detect(root, settings)
    if command is None:
        return say(
            "Test gate is on in this project but did not run: no runner was "
            "detected and .claude/test-gate.json names no usable command. This "
            "turn ended without tests. Set \"command\" in "
            ".claude/test-gate.json, or make .claude/test-gate.sh executable.",
            keep_going=False)

    timeout = effective_timeout(settings)

    printable = shlex.join(command) if hasattr(shlex, "join") else " ".join(command)
    try:
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return say(
            f"The project's test gate ran `{printable}` in {root} and killed it "
            f"after {timeout}s with no result.\n"
            + ("The turn is ending with the gate unresolved: it already "
               "blocked once and the command still does not finish."
               if reentry else
               "Re-run it yourself with a per-test timeout (pytest --timeout=60, "
               "mvn -Dsurefire.timeout=60), find the test that hangs, fix it and "
               "report which one it was. Do not raise the gate's timeout to get "
               "past this."),
            keep_going=not reentry)
    except Exception as error:
        return say(f"Test gate could not start `{printable}`: {error}. This turn "
                   "ended without tests.", keep_going=False)

    if result.returncode == 0:
        return 0

    output = (result.stdout or "") + "\n" + (result.stderr or "")
    detail = first_failure(output)
    if detail is None:
        detail = "\n".join(output.strip().splitlines()[-40:])
        heading = "Last lines of output"
    else:
        heading = "First failure"

    if reentry:
        # The gate has already blocked this turn once and just re-ran, so the
        # fix it asked for has been checked. It is still red, and a second
        # block would only loop: the turn ends, and the user is told.
        return say(
            f"The project's test gate ran `{printable}` again in {root} after "
            f"blocking once; it still exits {result.returncode}.\n\n"
            f"{heading}:\n{bounded(detail)}\n\n"
            "The turn was allowed to end with the suite red rather than "
            "blocked a second time.",
            keep_going=False)

    return say(
        f"The project's test gate ran `{printable}` in {root} before letting "
        f"this turn end; it exited {result.returncode}.\n\n"
        f"{heading}:\n{bounded(detail)}\n\n"
        "Fix the code so this command passes. Do not delete, skip, xfail or "
        "loosen a test to get green; if you think a test is wrong, stop and "
        "tell the user which test and why.\n\n"
        "If the task was to verify, review or check rather than to fix, this "
        "failure is the answer: report it, with this output and its cause, "
        "and say the change is not verified. Do not ask the user for "
        "permission to finish. The gate runs again on your next stop to check "
        "any fix, and it will not block a second time.",
        keep_going=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
