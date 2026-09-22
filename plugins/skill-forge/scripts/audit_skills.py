#!/usr/bin/env python3
"""Audit a skills directory for the reasons a skill fails to fire.

Run against a directory holding skills, or a single skill directory:

    python3 audit_skills.py .claude/skills
    python3 audit_skills.py ~/.claude/skills/my-skill
    python3 audit_skills.py plugins/*/skills --json

Exit 0 when nothing is wrong, 1 when any error is found. Warnings alone do not
fail the run — they are judgement calls, not violations.

This script is run, not read: it never enters the model's context, which is
what lets it be this long.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

NAME_MAX = 64
DESCRIPTION_MAX = 1024
BODY_MAX_LINES = 500

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# A description has to answer "when do I use this", not only "what is this".
# These are the shapes that answer it.
TRIGGER_HINTS = (
    "use when", "use this when", "when the user", "when you", "when a",
    "for when", "apply when", "invoked when", "triggered", "before ",
    "after ", "whenever",
)

KNOWN_TOOLS = {
    "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Task",
    "TodoWrite", "WebFetch", "WebSearch", "Write", "Skill", "SlashCommand",
}

KNOWN_MODELS = {"haiku", "sonnet", "opus", "inherit"}


class Finding:
    def __init__(self, level, skill, message, hint=None, rule=None):
        self.level = level
        self.skill = skill
        self.message = message
        self.hint = hint
        self.rule = rule

    def as_dict(self):
        return {
            "level": self.level,
            "rule": self.rule,
            "skill": self.skill,
            "message": self.message,
            "hint": self.hint,
        }


def parse_frontmatter(text):
    """(frontmatter dict, body, error). A deliberately small YAML subset:
    flat `key: value` pairs, which is all a SKILL.md header should hold."""
    if not text.startswith("---"):
        return None, text, "no YAML frontmatter"

    end = text.find("\n---", 3)
    if end == -1:
        return None, text, "frontmatter is never closed with ---"

    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")

    data, key = {}, None
    for line in raw.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and key:
            data[key] = (data[key] + " " + line.strip()).strip()
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith((">", "|")):
            value = ""
        data[key] = value.strip("\"'")
    return data, body, None


def tokens(text):
    return {w for w in re.findall(r"[a-z]{4,}", text.lower())}


def tool_entries(raw):
    """Split an `allowed-tools` value into entries, in any of the forms Claude
    Code accepts: comma- or space-separated, a flow list `[a, b]`, or a block
    list (which the frontmatter parser flattens to `- a - b`). Parentheses are
    respected, so `Bash(git add *)` stays one entry."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    entries, current, depth = [], "", 0
    for char in raw:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if depth == 0 and (char == "," or char.isspace()):
            if current:
                entries.append(current)
            current = ""
            continue
        current += char
    if current:
        entries.append(current)
    return [e.strip("\"'") for e in entries if e not in {"-", ""}]


# A grant, not a restriction: every tool listed runs without a prompt on the
# turn the skill fires. These entries hand over the whole tool.
BARE_SHELL = {"Bash", "Bash(*)", "Bash(:*)", "PowerShell", "PowerShell(*)"}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}


def find_skills(target):
    """Every SKILL.md under this path, the directories that look like a skill
    but have none, and any SKILL.md sitting loose in a skills root."""
    target = Path(target)
    found, missing, loose = [], [], []

    if target.is_file() and target.name == "SKILL.md":
        return [target], [], []

    if not target.is_dir():
        return [], [], []

    # A directory holding SKILL.md is one skill, unless it also holds skill
    # directories: then it is a skills root, and its SKILL.md is loose.
    has_children = any(
        (entry / "SKILL.md").is_file()
        for entry in target.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )
    if (target / "SKILL.md").is_file() and not has_children:
        return [target / "SKILL.md"], [], []

    for entry in sorted(target.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        skill_file = entry / "SKILL.md"
        if skill_file.is_file():
            found.append(skill_file)
        else:
            stray = list(entry.glob("*.md"))
            if stray or (entry / "scripts").is_dir() or (entry / "references").is_dir():
                missing.append(entry)

    # A SKILL.md sitting loose in the skills root: a real and common mistake,
    # because the skill silently never loads.
    if (target / "SKILL.md").is_file():
        loose.append(target / "SKILL.md")

    return found, missing, loose


def audit_one(path, findings):
    directory = path.parent
    label = directory.name

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as error:
        findings.append(Finding("error", label, f"cannot read SKILL.md: {error}"))
        return None

    data, body, error = parse_frontmatter(text)
    if error:
        findings.append(Finding(
            "error", label, error,
            "A skill without frontmatter never loads: name and description are "
            "the only things read at startup."))
        return None

    name = data.get("name", "")
    description = data.get("description", "")

    # --- name ---
    if not name:
        findings.append(Finding("error", label, "frontmatter has no `name`"))
    else:
        if len(name) > NAME_MAX:
            findings.append(Finding(
                "error", label,
                f"`name` is {len(name)} characters, over the {NAME_MAX} limit"))
        if not NAME_PATTERN.match(name):
            findings.append(Finding(
                "error", label,
                f"`name` is {name!r}: use lowercase letters, digits and single "
                f"hyphens"))
        if name != directory.name:
            findings.append(Finding(
                "error", label,
                f"`name` is {name!r} but the directory is {directory.name!r}",
                "They have to match, or the skill does not resolve."))

    # --- description ---
    if not description:
        findings.append(Finding(
            "error", label, "frontmatter has no `description`",
            "This is the field that decides whether the skill ever fires."))
    else:
        if len(description) > DESCRIPTION_MAX:
            findings.append(Finding(
                "error", label,
                f"`description` is {len(description)} characters, over the "
                f"{DESCRIPTION_MAX} limit"))
        if len(description) < 40:
            findings.append(Finding(
                "warning", label,
                f"`description` is only {len(description)} characters",
                "Too short to match on. Say what it does AND when to use it."))
        lowered = description.lower()
        if not any(hint in lowered for hint in TRIGGER_HINTS):
            findings.append(Finding(
                "warning", label,
                "`description` never says when to use the skill",
                "It reads as a definition. Add the situation in the words a "
                "user would actually type."))
        if description.strip().lower().startswith(("this skill", "a skill")):
            findings.append(Finding(
                "warning", label,
                "`description` opens with \"this skill\"",
                "Spend those characters on the trigger instead."))

    # --- optional fields ---
    allowed = data.get("allowed-tools", "")
    if allowed:
        entries = tool_entries(allowed)
        declared = {entry.split("(", 1)[0] for entry in entries}
        unknown = declared - KNOWN_TOOLS - {"PowerShell"}
        if unknown:
            findings.append(Finding(
                "warning", label,
                f"`allowed-tools` names unknown tool(s): {', '.join(sorted(unknown))}"))
        bare = sorted(set(entries) & BARE_SHELL)
        if bare:
            findings.append(Finding(
                "error", label,
                f"`allowed-tools` pre-approves every shell command ({', '.join(bare)})",
                "The field grants, it does not restrict: whenever the skill fires, "
                "any command runs without a prompt. Scope it to the script the "
                "skill runs, e.g. Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check.py *).",
                rule="bare-bash"))
        writes = sorted(set(entries) & WRITE_TOOLS)
        if writes:
            findings.append(Finding(
                "warning", label,
                f"`allowed-tools` pre-approves file writes ({', '.join(writes)})",
                "Every write on the turn the skill fires goes through without a "
                "prompt. Leave writes to the normal permission flow.",
                rule="write-grant"))

    model = data.get("model", "")
    if model and model not in KNOWN_MODELS:
        findings.append(Finding(
            "warning", label,
            f"`model` is {model!r}, expected one of {', '.join(sorted(KNOWN_MODELS))}"))

    # --- body ---
    line_count = len(body.splitlines())
    if line_count > BODY_MAX_LINES:
        findings.append(Finding(
            "error", label,
            f"body is {line_count} lines, over the {BODY_MAX_LINES} limit",
            "Move the long material to references/ and point at it: those "
            "files load only when needed."))
    elif line_count > BODY_MAX_LINES * 0.8:
        findings.append(Finding(
            "warning", label,
            f"body is {line_count} lines, close to the {BODY_MAX_LINES} limit"))
    if line_count == 0:
        findings.append(Finding("error", label, "body is empty"))

    # --- supporting files ---
    for script in directory.glob("scripts/*"):
        if script.suffix in {".sh", ".py"} and not os.access(script, os.X_OK):
            findings.append(Finding(
                "warning", label,
                f"scripts/{script.name} is not executable",
                "chmod +x it, or it cannot be run without a shell prefix."))

    for reference in directory.glob("references/*"):
        if reference.name not in body:
            findings.append(Finding(
                "warning", label,
                f"references/{reference.name} is never mentioned in SKILL.md",
                "A reference nothing points at is never loaded."))

    return {"name": name or label, "description": description, "label": label}


def neighbours(target):
    """Agents and commands sitting beside a skills directory.

    A skill does not compete only with other skills. It competes with the
    agents and commands installed alongside it, which the model chooses
    between on the same evidence: their descriptions.
    """
    target = Path(target)
    if target.is_file():
        target = target.parent
    plugin = target.parent if target.name == "skills" else None
    if plugin is None:
        return []

    others = []
    for kind, subdir in (("agent", "agents"), ("command", "commands")):
        for path in sorted((plugin / subdir).glob("*.md")):
            try:
                data, _, error = parse_frontmatter(path.read_text(encoding="utf-8"))
            except OSError:
                continue
            if error or not data.get("description"):
                continue
            others.append({
                "name": data.get("name") or path.stem,
                "description": data["description"],
                "label": f"{kind} {path.stem}",
            })
    return others


def check_overlap(skills, findings, others=()):
    """Two descriptions that match the same prompts make the choice arbitrary."""
    def compare(first, second, hint):
        a, b = tokens(first["description"]), tokens(second["description"])
        if not a or not b:
            return
        overlap = len(a & b) / min(len(a), len(b))
        if overlap > 0.6:
            findings.append(Finding(
                "warning", first["label"],
                f"description overlaps {int(overlap * 100)}% with "
                f"{second['label']!r}", hint))

    for i, first in enumerate(skills):
        for second in skills[i + 1:]:
            compare(first, second,
                    "When both match a prompt, which one fires is arbitrary. "
                    "Make each name the situation the other does not cover.")
        for other in others:
            compare(first, other,
                    "The model picks between a skill, an agent and a command "
                    "on their descriptions alone. Say what this one does that "
                    "the other does not — or drop one of them.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="skills directory, or a skill")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    findings, skills, audited = [], [], 0
    others = []

    for target in args.paths:
        others.extend(neighbours(target))
        found, missing, loose = find_skills(target)
        for path in loose:
            findings.append(Finding(
                "error", f"{path.parent.name}/SKILL.md",
                "SKILL.md sits loose in the skills root, so it never loads",
                "Move it into a directory named after the skill: "
                f"{path.parent.name}/<name>/SKILL.md."))
        for directory in missing:
            findings.append(Finding(
                "error", directory.name,
                "directory looks like a skill but has no SKILL.md",
                "The file has to be named SKILL.md, inside a directory named "
                "after the skill."))
        for path in found:
            audited += 1
            result = audit_one(path, findings)
            if result:
                skills.append(result)

    check_overlap(skills, findings, others)

    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]

    if args.json:
        print(json.dumps({
            "audited": audited,
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
        return 1 if errors else 0

    if not audited:
        print("No skills found. Point this at a directory of skill directories.")
        return 0

    for finding in findings:
        mark = "ERROR" if finding.level == "error" else "warn "
        print(f"{mark}  {finding.skill}: {finding.message}")
        if finding.hint:
            print(f"        {finding.hint}")

    if not findings:
        print(f"Clean — {audited} skill(s) audited, nothing to report.")
    else:
        print()
        print(f"{audited} skill(s) audited: {len(errors)} error(s), "
              f"{len(warnings)} warning(s)")

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
