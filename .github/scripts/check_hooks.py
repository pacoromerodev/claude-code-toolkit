#!/usr/bin/env python3
"""Every hooks.json points at a script that exists, by a path that resolves.

A hook with a wrong path does not fail loudly. It fails the way a missing
guard fails: nothing happens, and nothing says so. The three ways to get there
are a relative command (resolved against whatever directory the session
started in), `$CLAUDE_PROJECT_DIR` in a plugin (that is the user's project,
not the plugin), and a `${CLAUDE_PLUGIN_ROOT}` path to a script that was
renamed.

An event name that is not an event is the fourth: the object is accepted and
the entry never fires.

Usage: check_hooks.py [repository root]
Exit 0 when every hook file is sound, 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EVENTS = {
    "PreToolUse", "PostToolUse", "Notification", "UserPromptSubmit", "Stop",
    "SubagentStop", "PreCompact", "PostCompact", "SessionStart", "SessionEnd",
}

# Events that hold the session while the hook runs, so a hang is visible to
# whoever is waiting.
BLOCKING = {"Stop", "SubagentStop", "PreCompact", "PostCompact", "SessionStart"}

PLUGIN_ROOT = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/([^\"'\s]+)")


def check_command(command, plugin, where, problems):
    if "${CLAUDE_PLUGIN_ROOT}" not in command and "$CLAUDE_PLUGIN_ROOT" not in command:
        if "$CLAUDE_PROJECT_DIR" in command:
            problems.append(
                f"{where}: uses $CLAUDE_PROJECT_DIR — that is the user's "
                f"project, not this plugin. A plugin's own scripts live under "
                f"${{CLAUDE_PLUGIN_ROOT}}"
            )
        elif re.search(r"(^|\s)\.{1,2}/", command):
            problems.append(
                f"{where}: relative path in {command!r} — it resolves against "
                f"whatever directory the session started in, so the hook "
                f"silently does not run"
            )
        return

    for match in PLUGIN_ROOT.finditer(command):
        target = plugin / match.group(1).strip("\"'")
        if not target.exists():
            problems.append(
                f"{where}: {match.group(1)} does not exist in the plugin"
            )


def check_file(path, plugin, root, problems):
    shown = path.relative_to(root).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        problems.append(f"{shown}: not valid JSON: {error}")
        return

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        problems.append(f"{shown}: no top-level \"hooks\" object")
        return

    for event, entries in hooks.items():
        if event not in EVENTS:
            problems.append(
                f"{shown}: {event!r} is not a hook event, so the entry never "
                f"fires. Events are: " + ", ".join(sorted(EVENTS))
            )
            continue
        if not isinstance(entries, list):
            problems.append(f"{shown}: {event} is not a list of matchers")
            continue

        for index, entry in enumerate(entries):
            where = f"{shown}: {event}[{index}]"
            for hook in (entry.get("hooks") or []) if isinstance(entry, dict) else []:
                command = hook.get("command")
                if hook.get("type") != "command" or not isinstance(command, str):
                    problems.append(f"{where}: not a command hook")
                    continue
                check_command(command, plugin, where, problems)
                if event in BLOCKING and "timeout" not in hook:
                    problems.append(
                        f"{where}: no timeout on an event that holds the "
                        f"session. A hook that hangs here leaves it unable to "
                        f"finish"
                    )


def main(root=ROOT):
    problems = []
    files = sorted((root / "plugins").glob("*/hooks/hooks.json"))
    for path in files:
        check_file(path, path.parents[1], root, problems)

    if problems:
        print("Hook check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        print("\nA hook that does not resolve does not report anything: it "
              "just never runs.")
        return 1

    print(f"OK — {len(files)} hook file(s) point at scripts that exist")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
