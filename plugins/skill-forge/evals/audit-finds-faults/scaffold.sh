#!/usr/bin/env bash
# Two skills, two faults: one name does not match its directory (so it never
# resolves at all), and one description is a definition with no trigger.
set -euo pipefail

mkdir -p .claude/skills/changelog-entry .claude/skills/migration-check

cat > .claude/skills/changelog-entry/SKILL.md <<'SKILL'
---
name: write-changelog
description: Writes a changelog entry from the commit range. Use when the user is preparing a release or asks what changed.
---
Collect the commits since the last tag and group them.
SKILL

cat > .claude/skills/migration-check/SKILL.md <<'SKILL'
---
name: migration-check
description: This skill provides database migration review capabilities.
---
Check the changeset for unsafe operations.
SKILL
