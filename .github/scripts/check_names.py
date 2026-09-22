#!/usr/bin/env python3
"""Two components with one name, and the model only ever sees one of them.

`claude plugin details skill-forge` once listed `audit-skills, audit-skills`:
a command and a skill with the same name inside one plugin. The command won,
so the skill's description — the part that says *when* to use it, the part the
model matches a prompt against — never reached the model at all. Nothing in
the repository could see that, because each component was valid on its own.

Checked here:

  error    a command and a skill with the same name in one plugin
  warning  a command and an agent with the same name in one plugin
  warning  one name used by two different plugins
  warning  a name Claude Code already ships as a command

Usage: check_names.py [repository root]
Exit 0 when there is no error, 1 otherwise. Warnings are judgement calls.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Commands Claude Code ships, from its slash-command reference (read
# 2026-09-22, code.claude.com/docs/en/slash-commands), plus `review`, which
# that page documents as a bundled alias of `code-review`. Kept here rather
# than guessed: a warning naming a command that does not exist is worse than
# no warning.
BUILT_IN = {
    "add-dir", "batch", "claude-api", "cd", "code-review", "compact",
    "context", "debug", "doctor", "help", "init", "login", "loop", "model",
    "permissions", "plugin", "reload-plugins", "rewind", "review", "run",
    "run-skill-generator", "security-review", "skill-doctor", "skills",
    "verify",
}

FRONTMATTER_NAME = re.compile(r"^name:\s*(.+?)\s*$", re.M)


class Finding:
    def __init__(self, level, where, message, hint):
        self.level, self.where, self.message, self.hint = level, where, message, hint


def declared_name(path, fallback):
    """The frontmatter name if there is one, else the file or directory name."""
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except OSError:
        return fallback
    if not head.startswith("---"):
        return fallback
    match = FRONTMATTER_NAME.search(head.split("---", 2)[1] if "---" in head[3:] else "")
    return match.group(1).strip("\"'") if match else fallback


def components(plugin):
    """{kind: {name: path}} for the three kinds that get invoked by name."""
    found = {"skill": {}, "agent": {}, "command": {}}
    for directory in sorted((plugin / "skills").glob("*/")):
        skill_file = directory / "SKILL.md"
        if skill_file.is_file():
            found["skill"][declared_name(skill_file, directory.name)] = skill_file
    # An agent is identified by its frontmatter name; a command is identified
    # by its filename, whatever its frontmatter says.
    for path in sorted((plugin / "agents").glob("*.md")):
        found["agent"][declared_name(path, path.stem)] = path
    for path in sorted((plugin / "commands").glob("*.md")):
        found["command"][path.stem] = path
    return found


def main(root=ROOT):
    findings = []
    everywhere = {}  # name -> [ (plugin, kind) ]

    plugins = sorted(p for p in (root / "plugins").glob("*/") if p.is_dir())
    total = 0
    for plugin in plugins:
        found = components(plugin)
        total += sum(len(entries) for entries in found.values())
        label = plugin.name

        for name in sorted(set(found["command"]) & set(found["skill"])):
            findings.append(Finding(
                "error", f"{label}:{name}",
                "a command and a skill share this name",
                "The command shadows the skill: its description is what the "
                "model sees, so the skill's trigger text never reaches it. "
                "Rename one, or delete the command and let the skill fire on "
                "its own description."))

        for name in sorted(set(found["command"]) & set(found["agent"])):
            findings.append(Finding(
                "warning", f"{label}:{name}",
                "a command and an agent share this name",
                "Legitimate when the command exists to launch that agent. "
                "Worth a look when it does not: one of them is listed and "
                "the other is guessed at."))

        for kind, entries in found.items():
            for name in entries:
                everywhere.setdefault(name, []).append((label, kind))
                if name in BUILT_IN:
                    findings.append(Finding(
                        "warning", f"{label}:{name}",
                        f"Claude Code already ships a command called {name!r}",
                        "The short form is ambiguous at best and runs the "
                        "built-in at worst. Either rename it, or document the "
                        f"namespaced form /{label}:{name}."))

    for name, holders in sorted(everywhere.items()):
        owners = sorted({plugin for plugin, _ in holders})
        if len(owners) > 1:
            findings.append(Finding(
                "warning", name,
                "used by " + " and ".join(owners),
                "Two plugins installed together put two components with one "
                "name in front of the model."))

    errors = [f for f in findings if f.level == "error"]
    for finding in findings:
        mark = "ERROR" if finding.level == "error" else "warn "
        print(f"{mark}  {finding.where}: {finding.message}")
        print(f"        {finding.hint}")

    if not findings:
        print(f"OK — {total} component name(s) across {len(plugins)} plugin(s), no collisions")
    else:
        print()
        print(f"{total} component name(s): {len(errors)} error(s), "
              f"{len(findings) - len(errors)} to look at")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
