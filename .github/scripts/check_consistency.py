#!/usr/bin/env python3
"""Every plugin directory has a marketplace entry, and their versions agree.

`claude plugin validate` checks each manifest in isolation. It does not notice
that a new plugin was never added to the catalogue, or that plugin.json was
bumped and the marketplace entry was not — which is the failure that makes
`claude plugin tag` refuse a release.

Usage: check_consistency.py [repository root]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# A directory under plugins/ that holds none of these is scaffolding or a
# leftover, not a plugin someone forgot to finish.
PLUGIN_SIGNS = ("skills", "agents", "commands", "hooks", "scripts", "evals",
                "README.md", "CHANGELOG.md")


def load(path, root):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as error:
        print(f"error: {shown(path, root)} is not valid JSON: {error}")
        sys.exit(1)


def shown(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main(root=ROOT):
    marketplace = load(root / ".claude-plugin" / "marketplace.json", root)
    if marketplace is None:
        print("error: .claude-plugin/marketplace.json is missing")
        return 1

    entries = {}
    for entry in marketplace.get("plugins", []):
        name = entry.get("name")
        if not name:
            print("error: a marketplace entry has no name")
            return 1
        if name in entries:
            print(f"error: {name} appears twice in marketplace.json")
            return 1
        entries[name] = entry

    problems = []
    seen = set()

    # A directory with no manifest used to be skipped in silence, so a plugin
    # whose manifest was never written looked like a repository with one fewer
    # plugin (AUDIT L5).
    for directory in sorted((root / "plugins").glob("*/")):
        if not directory.is_dir() or (directory / ".claude-plugin" / "plugin.json").is_file():
            continue
        if any((directory / sign).exists() for sign in PLUGIN_SIGNS):
            problems.append(
                f"{shown(directory, root)}: no .claude-plugin/plugin.json — "
                f"nothing here is installable, and every other check skips it"
            )

    for manifest_path in sorted((root / "plugins").glob("*/.claude-plugin/plugin.json")):
        directory = manifest_path.parents[1]
        rel = shown(directory, root)
        manifest = load(manifest_path, root)
        name = manifest.get("name")

        if name != directory.name:
            problems.append(
                f"{rel}: plugin.json name is {name!r} but the directory is "
                f"{directory.name!r} — they must match"
            )
            continue
        seen.add(name)

        entry = entries.get(name)
        if entry is None:
            problems.append(
                f"{rel}: no entry in marketplace.json — the plugin exists but "
                f"nobody can install it"
            )
            continue

        source = entry.get("source", "")
        expected = f"./{rel}"
        if source != expected:
            problems.append(
                f"{name}: marketplace source is {source!r}, expected {expected!r}"
            )

        manifest_version = manifest.get("version")
        entry_version = entry.get("version")
        if manifest_version != entry_version:
            problems.append(
                f"{name}: version mismatch — plugin.json says "
                f"{manifest_version!r}, marketplace.json says {entry_version!r}"
            )

        for required in ("description", "version"):
            if not manifest.get(required):
                problems.append(f"{rel}: plugin.json is missing {required}")

        if not (directory / "README.md").is_file():
            problems.append(f"{rel}: no README.md")
        if not (directory / "CHANGELOG.md").is_file():
            problems.append(f"{rel}: no CHANGELOG.md")
        # The manifest names a licence; the text itself has to travel with the
        # plugin, because an install copies the plugin directory and nothing
        # above it.
        if not (directory / "LICENSE").is_file():
            problems.append(
                f"{rel}: no LICENSE — an installed copy carries no licence text"
            )
        if not any(directory.glob("evals/*/case.yaml")) and not any(
            directory.glob("evals/*/prompt.md")
        ):
            problems.append(f"{rel}: no eval suite under evals/")

    for orphan in sorted(set(entries) - seen):
        problems.append(
            f"{orphan}: listed in marketplace.json but plugins/{orphan}/ does "
            f"not exist"
        )

    if problems:
        print("Consistency check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK — {len(seen)} plugin(s) consistent with the marketplace")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
