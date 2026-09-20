#!/usr/bin/env python3
"""Check a Claude Code settings file for gaps that only show up later.

    python3 check_settings.py .claude/settings.json
    python3 check_settings.py managed-settings.json --managed --json

A settings file is where a rollout's decisions end up, and most of what goes
wrong with one is an omission rather than an error: nothing was said about
marketplaces, so any developer can add any; permissions were widened for one
task and never narrowed; a secret was pasted into an environment variable.

With `--managed`, the file is held to the stricter bar an organisation-wide
policy needs.

Exit 1 on an error, 0 otherwise.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Permission entries that grant far more than they appear to.
BROAD_ALLOW = {
    "Bash", "Bash(*)", "Bash(*:*)", "Write", "Write(*)", "Edit", "Edit(*)",
    "WebFetch", "WebFetch(*)", "Read(*)", "*",
}

# Things that should never appear as a literal value in a settings file.
SECRETLIKE = re.compile(
    r"\b(sk-ant-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,})")

SECRET_KEY_NAME = re.compile(
    r"(api_?key|token|secret|password|credential)", re.I)

DANGEROUS_FLAGS = {
    "dangerouslySkipPermissions": "bypasses every permission check",
    "bypassPermissions": "bypasses every permission check",
}


class Finding:
    def __init__(self, level, path, rule, message, hint):
        self.level, self.path, self.rule = level, path, rule
        self.message, self.hint = message, hint

    def as_dict(self):
        return {"level": self.level, "path": self.path, "rule": self.rule,
                "message": self.message, "hint": self.hint}


def walk_strings(node, trail=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{trail}.{key}" if trail else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, f"{trail}[{index}]")
    elif isinstance(node, str):
        yield trail, node


def check(data, managed, findings):
    permissions = data.get("permissions") or {}
    allow = permissions.get("allow") or []
    deny = permissions.get("deny") or []
    mode = permissions.get("defaultMode")

    # --- permissions ---
    for entry in allow:
        if entry in BROAD_ALLOW:
            findings.append(Finding(
                "error" if managed else "warning",
                f"permissions.allow[{entry}]", "broad-allow",
                f"{entry!r} allows the whole tool, not a pattern",
                "Grant the narrowest form that works — Bash(npm test:*) "
                "rather than Bash. A blanket allow never gets narrowed back "
                "once someone has stopped being prompted."))

    if mode in {"bypassPermissions", "dangerously-skip-permissions"}:
        findings.append(Finding(
            "error", "permissions.defaultMode", "bypass-default",
            f"defaultMode is {mode!r}",
            "This disables the permission system for every session using this "
            "file. Acceptable inside a disposable VM, never as a default."))

    if managed and not deny:
        findings.append(Finding(
            "warning", "permissions.deny", "no-deny",
            "no deny list",
            "An allow list says what is permitted; a deny list holds even "
            "when a project file widens things. Credentials, history files "
            "and production config belong here."))

    if managed and mode is None:
        findings.append(Finding(
            "warning", "permissions.defaultMode", "no-default-mode",
            "defaultMode is not set",
            "Without it, each machine keeps whatever mode it was last left "
            "in. Say what the organisation's default is."))

    # --- marketplaces and plugins ---
    if managed and "strictKnownMarketplaces" not in json.dumps(data):
        findings.append(Finding(
            "warning", "strictKnownMarketplaces", "open-marketplaces",
            "marketplaces are not restricted",
            "A plugin runs code with the user's privileges and its hooks "
            "stack with everyone else's. Pin the marketplaces people may "
            "install from."))

    # --- secrets ---
    for path, value in walk_strings(data):
        if SECRETLIKE.search(value):
            findings.append(Finding(
                "error", path, "secret-value",
                "a literal credential appears in this file",
                "Settings files get committed and shared. Reference an "
                "environment variable instead, and rotate this value — it "
                "should be treated as leaked."))
        elif SECRET_KEY_NAME.search(path) and value and \
                not value.startswith("$") and "${" not in value and \
                len(value) > 12:
            findings.append(Finding(
                "warning", path, "secret-key",
                f"{path} holds a literal value",
                "A key with this name should reference the environment, not "
                "carry the value."))

    # --- flags ---
    for flag, why in DANGEROUS_FLAGS.items():
        if data.get(flag) is True:
            findings.append(Finding(
                "error", flag, "dangerous-flag",
                f"{flag} is true, which {why}",
                "Remove it. If a specific workflow needs it, scope it to that "
                "workflow rather than the whole configuration."))

    # --- hooks ---
    hooks = data.get("hooks") or {}
    for event, entries in hooks.items():
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            for hook in (entry.get("hooks") or []):
                command = hook.get("command", "")
                if isinstance(command, str):
                    if command.startswith("./") or command.startswith("../"):
                        findings.append(Finding(
                            "error", f"hooks.{event}[{index}]", "relative-hook",
                            f"hook command is a relative path: {command!r}",
                            "It resolves against whatever directory the "
                            "session started in. Use $CLAUDE_PROJECT_DIR or "
                            "${CLAUDE_PLUGIN_ROOT}."))
                    if "timeout" not in hook and event in {"Stop", "PreCompact",
                                                           "SessionStart"}:
                        findings.append(Finding(
                            "info", f"hooks.{event}[{index}]", "no-timeout",
                            "no timeout on a hook that can block a session",
                            "Give it one. A hook that hangs on this event "
                            "leaves the session unable to finish."))

    # --- retention and visibility, for a managed policy ---
    if managed:
        for key, message, hint in (
            ("env", "no shared environment variables set",
             "This is where a proxy, a region or a default model is pinned "
             "for everyone."),
            ("model", "no default model set",
             "Without one, every user's default applies — which is also where "
             "unplanned spend comes from."),
        ):
            if key not in data:
                findings.append(Finding("info", key, "missing-key", message, hint))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--managed", action="store_true",
                        help="hold the file to the organisation-policy bar")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings, checked = [], 0
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            findings.append(Finding("error", str(path), "missing",
                                    "file not found", ""))
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            findings.append(Finding(
                "error", str(path), "invalid-json",
                f"not valid JSON: {error}",
                "Claude Code ignores a settings file it cannot parse — "
                "silently, so every rule in it stops applying."))
            continue
        checked += 1
        managed = args.managed or "managed" in path.name
        check(data, managed, findings)

    errors = [f for f in findings if f.level == "error"]

    if args.json:
        print(json.dumps({
            "checked": checked, "errors": len(errors),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
        return 1 if errors else 0

    order = {"error": 0, "warning": 1, "info": 2}
    for finding in sorted(findings, key=lambda f: (order[f.level], f.path)):
        mark = {"error": "ERROR", "warning": "warn ", "info": "note "}[finding.level]
        print(f"{mark}  {finding.path}  [{finding.rule}]")
        print(f"        {finding.message}")
        if finding.hint:
            print(f"        → {finding.hint}")

    print()
    if not findings:
        print(f"Clean — {checked} settings file(s), nothing to report.")
    else:
        print(f"{checked} file(s): {len(errors)} error(s), "
              f"{len(findings) - len(errors)} to look at")

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
