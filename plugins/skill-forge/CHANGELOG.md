# Changelog

All notable changes to `skill-forge`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-09-20

### Added
- `write-a-skill` skill: scaffolds a skill correctly and, more importantly,
  spends its length on the description — the only field loaded at startup and
  the reason most skills never fire.
- `audit-skills` skill wrapping `scripts/audit_skills.py`: finds name/directory
  mismatches, missing or unclosed frontmatter, missing descriptions,
  descriptions with no trigger, oversized bodies, misplaced `SKILL.md` files,
  non-executable scripts, unreferenced `references/` files, and descriptions
  that overlap each other.
- `skill-describer` subagent: writes three candidate descriptions that differ
  in coverage — narrow, broad, balanced — and names what each would and would
  not match, including likely false positives.
- `/new-skill` and `/audit-skills` commands.
- 15 fixture assertions over a tree with planted faults and a clean tree; the
  suite also audits this repository's own skills.
