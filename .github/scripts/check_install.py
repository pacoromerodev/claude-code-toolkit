#!/usr/bin/env python3
"""Install every plugin from this checkout, and see what Claude Code loaded.

`claude plugin validate` reads each manifest. It does not add the marketplace,
install from it, or say which components the installed plugin ends up with, so
a skill directory Claude Code does not recognise, a hook event it ignores, or
a file the install leaves behind all pass it. This does the install a user
does, in a throwaway config directory, with no model and no login:

  - the marketplace adds from the repository root
  - every plugin in it installs, at the version its plugin.json declares
  - the installed copy holds the same files as plugins/<name>/
  - `claude plugin details` lists the skills, agents and hook events that are
    on disk, no more and no fewer

Usage: check_install.py [repository root]
Environment: CLAUDE_BIN, the claude executable (default: claude); tests use a
stub.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")

INVENTORY = re.compile(r"^[ \t]*(Skills|Agents|Hooks)[ \t]*\((\d+)\)[ \t]*([^\n(]*?)[ \t]*(\([^\n]*\))?[ \t]*$", re.M)
NAME = re.compile(r"^name:\s*[\"']?(.+?)[\"']?\s*$", re.M)
IGNORED = {"__pycache__", ".DS_Store"}


def run(env, *args):
    result = subprocess.run([CLAUDE, *args], env=env, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def frontmatter_name(path, fallback):
    text = path.read_text(encoding="utf-8")
    if text.startswith("---") and text.count("---") >= 2:
        match = NAME.search(text.split("---", 2)[1])
        if match:
            return match.group(1)
    return fallback


def on_disk(directory):
    """What the plugin ships, by kind, read from the files themselves."""
    skills = {frontmatter_name(path, path.parent.name)
              for path in directory.glob("skills/*/SKILL.md")}
    agents = {frontmatter_name(path, path.stem)
              for path in directory.glob("agents/*.md")}
    hooks_file = directory / "hooks" / "hooks.json"
    hooks = set()
    if hooks_file.is_file():
        hooks = set(json.loads(hooks_file.read_text(encoding="utf-8")).get("hooks", {}))
    return {"Skills": skills, "Agents": agents, "Hooks": hooks}


def listed(details):
    found = {"Skills": set(), "Agents": set(), "Hooks": set()}
    for kind, _count, names, _note in INVENTORY.findall(details):
        found[kind] = {name.strip() for name in names.split(",") if name.strip()}
    return found


def files(directory):
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and not IGNORED & set(path.relative_to(directory).parts)
    }


def main(root=ROOT):
    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    market = marketplace["name"]
    problems = []

    with tempfile.TemporaryDirectory() as config:
        # A config directory of its own: nothing the person running this has
        # installed is read, and nothing is left behind in it.
        env = dict(os.environ, CLAUDE_CONFIG_DIR=config)
        code, out = run(env, "plugin", "marketplace", "add", str(root))
        if code != 0:
            print(f"error: the marketplace does not add from {root}:\n{out}")
            return 1

        installed = []
        for entry in marketplace.get("plugins", []):
            name = entry["name"]
            code, out = run(env, "plugin", "install", f"{name}@{market}")
            if code != 0:
                problems.append(f"{name}: does not install: {out.strip()}")
                continue
            installed.append(name)

        code, out = run(env, "plugin", "list", "--json")
        try:
            paths = {item["id"]: item for item in json.loads(out)} if code == 0 else {}
        except json.JSONDecodeError:
            paths = {}
        if not paths and installed:
            print(f"error: `claude plugin list --json` gave nothing to read:\n{out}")
            return 1

        for name in installed:
            directory = root / "plugins" / name
            item = paths.get(f"{name}@{market}")
            if item is None:
                problems.append(f"{name}: installed, but not in `claude plugin list`")
                continue

            declared = json.loads((directory / ".claude-plugin" / "plugin.json")
                                  .read_text(encoding="utf-8")).get("version")
            if item.get("version") != declared:
                problems.append(f"{name}: installed as {item.get('version')!r}, "
                                f"plugin.json says {declared!r}")

            copy = Path(item.get("installPath", ""))
            if copy.is_dir():
                missing = sorted(files(directory) - files(copy))
                extra = sorted(files(copy) - files(directory))
                if missing:
                    problems.append(f"{name}: the installed copy lacks {', '.join(missing)}")
                if extra:
                    problems.append(f"{name}: the installed copy has files the plugin "
                                    f"does not: {', '.join(extra)}")
            else:
                problems.append(f"{name}: installPath {copy} is not a directory")

            code, out = run(env, "plugin", "details", f"{name}@{market}")
            if code != 0:
                problems.append(f"{name}: `claude plugin details` failed: {out.strip()}")
                continue
            wanted, got = on_disk(directory), listed(out)
            for kind in ("Skills", "Agents", "Hooks"):
                for lost in sorted(wanted[kind] - got[kind]):
                    problems.append(f"{name}: {kind.lower()[:-1]} {lost!r} is on disk "
                                    f"but Claude Code did not load it")
                for stray in sorted(got[kind] - wanted[kind]):
                    problems.append(f"{name}: Claude Code lists {kind.lower()[:-1]} "
                                    f"{stray!r}, which nothing on disk declares")

    if problems:
        print("Install check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK — {len(installed)} plugin(s) install and load what they ship")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT))
