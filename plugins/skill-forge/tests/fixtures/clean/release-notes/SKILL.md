---
name: release-notes
description: Writes release notes from the commit range since the last tag, grouped by type and with breaking changes called out first. Use when the user is cutting a release, asks what changed since the last version, or asks to draft release notes or a changelog entry.
allowed-tools: Read, Grep, Bash(${CLAUDE_SKILL_DIR}/scripts/collect.sh *)
---

# Release notes

Collect the commits since the last tag, group them, and write the entry.

```bash
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

Breaking changes go first, under their own heading, with the migration step
for each. Everything else groups as Added / Changed / Fixed.

`scripts/collect.sh` produces the grouped list.
