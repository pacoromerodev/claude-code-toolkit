#!/usr/bin/env python3
"""Every settings file this repository ships must satisfy Claude Code's schema.

The reference templates in team-rollout are copied by whoever sets up a fleet.
Both of them failed the published schema: `strictKnownMarketplaces` was a
boolean where an array belongs, and a `$comment` sat inside `hooks`, where no
extra keys are allowed. Claude Code rejects a value the schema rejects, so a
policy that reads as restrictive applied nothing at all.

The schema is vendored (schema/claude-code-settings.schema.json) rather than
fetched, so CI does not depend on a network call, and updating it is a visible
commit. Refresh it with:

    curl -sSL -o .github/scripts/schema/claude-code-settings.schema.json \\
      https://json.schemastore.org/claude-code-settings.json

Unlike a plugin hook, this runs only in CI, so it may use jsonschema.

Usage: validate_settings_schema.py [file ...]   (default: the shipped files)
Exit 0 when every file validates, 1 otherwise.
"""
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - CI installs it
    print("jsonschema is not installed: python3 -m pip install jsonschema")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).resolve().parent / "schema" / "claude-code-settings.schema.json"
DEFAULT_FILES = sorted(
    list(ROOT.glob("plugins/*/settings/*.json"))
    + list(ROOT.glob("plugins/*/tests/fixtures/good-settings.json"))
)


def shown(path):
    """The path as it reads from the repository root, when it is inside it."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main(argv):
    files = [Path(p).resolve() for p in argv[1:]] or DEFAULT_FILES
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.validators.validator_for(schema)(schema)

    problems = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            problems.append(f"{path}: not valid JSON: {error}")
            continue
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            where = "/".join(str(part) for part in error.path) or "<root>"
            problems.append(f"{shown(path)}: at {where}: {error.message}")

    if problems:
        print("Settings schema check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        print("\nA value the schema rejects is a value Claude Code rejects: the "
              "file, or the entry, is skipped.")
        return 1

    print(f"OK — {len(files)} settings file(s) match the published schema")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
