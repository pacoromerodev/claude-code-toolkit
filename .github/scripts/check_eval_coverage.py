#!/usr/bin/env python3
"""Every skill has two prompts that must fire it and one that must not.

CONTRIBUTING has said this since the first release. Eight of the eighteen
skills had no case at all (AUDIT H6), because the rule lived in prose and
nothing counted. This counts.

A case declares what it exercises through its tags: the component's name, plus
`skill`, `subagent` or `hooks` for the kind, plus `negative` when the point is
that nothing fires. So:

    tags: [prompt-cache-audit, skill]        a positive case for that skill
    tags: [negative]                         a negative case for its plugin

Two positive cases per skill, one per subagent, and at least one negative case
in every plugin. A skill with `disable-model-invocation: true` is typed, like a
command: no prompt can fire it, so it has no routing to measure and, like a
command, it may be the subject of a case without having to be. Two, not one, because a single prompt worded like the
description proves only that the description matches itself.

Usage: check_eval_coverage.py [--enforce] [repository root]
Report-only by default; --enforce exits 1 when anything is short.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NAME = re.compile(r"^name:\s*(.+?)\s*$", re.M)
TAGS = re.compile(r"^tags:\s*\[(.*?)\]\s*$", re.M)
TYPED_ONLY = re.compile(r"^disable-model-invocation:\s*[\"']?true[\"']?\s*$", re.M | re.I)

POSITIVE_PER_SKILL = 2
POSITIVE_PER_AGENT = 1


def frontmatter_name(path, fallback):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return fallback
    if not text.startswith("---"):
        return fallback
    block = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    match = NAME.search(block)
    return match.group(1).strip("\"'") if match else fallback


def typed_only(path):
    """True when the model may not invoke the skill: only a person types it."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---") or text.count("---") < 2:
        return False
    return bool(TYPED_ONLY.search(text.split("---", 2)[1]))


def case_tags(path):
    text = path.read_text(encoding="utf-8")
    match = TAGS.search(text)
    if not match:
        return []
    return [tag.strip().strip("\"'") for tag in match.group(1).split(",") if tag.strip()]


def plugin_report(plugin):
    """(rows, negatives, unknown-tags) for one plugin."""
    skills = {}
    for directory in sorted((plugin / "skills").glob("*/")):
        skill_file = directory / "SKILL.md"
        if skill_file.is_file():
            skills[frontmatter_name(skill_file, directory.name)] = (
                "typed" if typed_only(skill_file) else "skill")
    typed = {name for name, kind in skills.items() if kind == "typed"}
    skills = {name: kind for name, kind in skills.items() if kind == "skill"}
    agents = {
        frontmatter_name(path, path.stem): "subagent"
        for path in sorted((plugin / "agents").glob("*.md"))
    }
    # A command may be the subject of a case; it just does not have to be.
    commands = {path.stem: "command"
                for path in sorted((plugin / "commands").glob("*.md"))}
    commands.update({name: "command" for name in typed})

    counts = {name: 0 for name in list(skills) + list(agents) + list(commands)}
    negatives = 0
    unknown = []

    for case in sorted((plugin / "evals").glob("*/case.yaml")):
        tags = case_tags(case)
        if "negative" in tags:
            negatives += 1
            continue
        for tag in tags:
            if tag in counts:
                counts[tag] += 1
            elif tag in {"skill", "subagent", "hooks", "needs-bash", "command"}:
                continue
            elif not (plugin / "scripts" / f"{tag}.py").is_file():
                unknown.append((case.parent.name, tag))

    rows = []
    for name, kind in list(skills.items()) + list(agents.items()):
        wanted = POSITIVE_PER_SKILL if kind == "skill" else POSITIVE_PER_AGENT
        rows.append((name, kind, counts[name], wanted))
    for name in commands:
        if counts[name]:
            rows.append((name, "command", counts[name], 0))
    return rows, negatives, unknown


def main(argv):
    enforce = "--enforce" in argv
    rest = [a for a in argv[1:] if not a.startswith("--")]
    root = Path(rest[0]).resolve() if rest else ROOT

    short, missing_negative, unknown_tags = [], [], []
    plugins = sorted(p for p in (root / "plugins").glob("*/") if p.is_dir())

    print(f"{'component':34} {'kind':9} {'have':>4} {'want':>4}")
    for plugin in plugins:
        rows, negatives, unknown = plugin_report(plugin)
        unknown_tags.extend((plugin.name, case, tag) for case, tag in unknown)
        if not rows and not negatives:
            continue
        print(f"\n{plugin.name}")
        for name, kind, have, want in rows:
            mark = " " if have >= want else "<"
            print(f"  {name:32} {kind:9} {have:>4} {want:>4} {mark}")
            if have < want:
                short.append(f"{plugin.name}:{name} has {have} of {want}")
        mark = " " if negatives else "<"
        print(f"  {'(negative cases)':32} {'negative':9} {negatives:>4} {1:>4} {mark}")
        if not negatives:
            missing_negative.append(plugin.name)

    print()
    for plugin, case, tag in unknown_tags:
        print(f"unknown tag: {plugin}/evals/{case} is tagged {tag!r}, which is "
              f"not a skill, a subagent or a script in that plugin")
    for line in short:
        print(f"short: {line}")
    for plugin in missing_negative:
        print(f"short: {plugin} has no negative case — a skill that fires on "
              f"everything costs context on every unrelated turn")

    problems = len(short) + len(missing_negative) + len(unknown_tags)
    if not problems:
        print("OK — every skill has two positive cases, every subagent one, "
              "every plugin a negative")
        return 0

    print(f"\n{problems} gap(s). "
          + ("Failing, because --enforce was given."
             if enforce else "Reporting only; pass --enforce to fail on these."))
    return 1 if enforce else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
