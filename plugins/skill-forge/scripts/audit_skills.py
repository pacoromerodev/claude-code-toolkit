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
    def __init__(self, level, skill, message, hint=None):
        self.level = level
        self.skill = skill
        self.message = message
        self.hint = hint

    def as_dict(self):
        return {
            "level": self.level,
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


def find_skills(target):
    """Every SKILL.md under this path, plus the directories that look like a
    skill but have none."""
    target = Path(target)
    found, missing = [], []

    if (target / "SKILL.md").is_file():
        return [target / "SKILL.md"], []

    if target.is_file() and target.name == "SKILL.md":
        return [target], []

    if not target.is_dir():
        return [], []

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

    # A SKILL.md sitting loose in the directory: a real and common mistake,
    # because the skill silently never loads.
    if (target / "SKILL.md").is_file():
        found.append(target / "SKILL.md")

    return found, missing


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
        declared = {t.strip() for t in re.split(r"[,\s]+", allowed) if t.strip()}
        unknown = declared - KNOWN_TOOLS
        if unknown:
            findings.append(Finding(
                "warning", label,
                f"`allowed-tools` names unknown tool(s): {', '.join(sorted(unknown))}"))

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


def check_overlap(skills, findings):
    """Two descriptions that match the same prompts make the choice arbitrary."""
    for i, first in enumerate(skills):
        for second in skills[i + 1:]:
            a, b = tokens(first["description"]), tokens(second["description"])
            if not a or not b:
                continue
            shared = a & b
            overlap = len(shared) / min(len(a), len(b))
            if overlap > 0.6:
                findings.append(Finding(
                    "warning", first["label"],
                    f"description overlaps {int(overlap * 100)}% with "
                    f"{second['label']!r}",
                    "When both match a prompt, which one fires is arbitrary. "
                    "Make each name the situation the other does not cover."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="skills directory, or a skill")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    findings, skills, audited = [], [], 0

    for target in args.paths:
        found, missing = find_skills(target)
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

    check_overlap(skills, findings)

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
