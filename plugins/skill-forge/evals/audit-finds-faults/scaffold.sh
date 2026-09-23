#!/usr/bin/env bash
# Two skills, two faults. One SKILL.md sits loose in the skills root instead of
# inside a directory of its own, so it never loads at all. The other loads, but
# its description is a definition with no trigger, so it fires only by luck.
set -euo pipefail

mkdir -p .claude/skills/migration-check

cat > .claude/skills/SKILL.md <<'SKILL'
---
name: changelog-entry
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
