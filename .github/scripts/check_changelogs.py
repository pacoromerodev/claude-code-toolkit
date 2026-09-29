#!/usr/bin/env python3
"""Every plugin's CHANGELOG.md says what the release it names contains.

skill-forge 0.2.0 once carried a second `### Added`, a third `### Added` and a
second `### Fixed` below its own sections: [Unreleased] blocks that a release
pasted under the version instead of merging, describing components the same
release removed. Each block was valid Markdown, so nothing noticed.

Checked here:

  a `###` section before any `## [version]` heading
  the same `###` section twice under one version
  a version heading that is not `[Unreleased]` or `[x.y.z]`
  versions that do not go strictly down the file
  a newest released version that is not the one plugin.json declares

Usage: check_changelogs.py [repository root]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VERSION = re.compile(r"^## \[(?P<name>[^\]]+)\]")
SECTION = re.compile(r"^### (?P<name>.+?)\s*$")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def shown(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def check(changelog, declared, rel):
    problems = []
    current = None
    sections = set()
    released = []

    for number, line in enumerate(changelog.read_text(encoding="utf-8").splitlines(), 1):
        where = f"{rel}:{number}"
        version = VERSION.match(line)
        if version:
            current = version.group("name")
            sections = set()
            if current == "Unreleased":
                continue
            parts = SEMVER.match(current)
            if not parts:
                problems.append(f"{where}: [{current}] is neither Unreleased nor x.y.z")
                continue
            released.append((tuple(int(p) for p in parts.groups()), current, where))
            continue

        section = SECTION.match(line)
        if not section:
            continue
        name = section.group("name")
        if current is None:
            problems.append(f"{where}: ### {name} comes before any version heading")
        elif name in sections:
            problems.append(
                f"{where}: a second ### {name} under [{current}] — merge it into "
                f"the first, or it belongs to another version"
            )
        sections.add(name)

    for (newer, newer_name, _), (older, older_name, where) in zip(released, released[1:]):
        if older >= newer:
            problems.append(
                f"{where}: [{older_name}] follows [{newer_name}] — versions must "
                f"go down the file"
            )

    if not released:
        problems.append(f"{rel}: no released version")
    elif released[0][1] != declared:
        problems.append(
            f"{rel}: the newest release is [{released[0][1]}] but plugin.json "
            f"says {declared!r}"
        )
    return problems


def main(root=ROOT):
    problems = []
    checked = 0
    for manifest_path in sorted((root / "plugins").glob("*/.claude-plugin/plugin.json")):
        directory = manifest_path.parents[1]
        changelog = directory / "CHANGELOG.md"
        if not changelog.is_file():
            continue  # check_consistency.py reports a missing changelog
        declared = json.loads(manifest_path.read_text(encoding="utf-8")).get("version")
        problems += check(changelog, declared, shown(changelog, root))
        checked += 1

    if problems:
        print("Changelog check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK — {checked} changelog(s) well formed and matching plugin.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
