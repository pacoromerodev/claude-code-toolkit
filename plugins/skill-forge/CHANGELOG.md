# Changelog

All notable changes to `skill-forge`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Added
- `audit_skills.py` reports a bare `Bash` in `allowed-tools` as an error and
  pre-approved `Write`/`Edit` as a warning, in every form the field accepts
  (comma- or space-separated, flow list, YAML list). `--json` findings carry a
  `rule` field.

### Changed
- `audit-finds-faults` eval plants a loose `SKILL.md` (never loads) instead of a
  name that differs from its directory, which Claude Code still loads.

### Fixed
- `audit_skills.py` treated a skills root holding a loose `SKILL.md` as a
  single skill: it audited only that file, misreported it as a name mismatch,
  and never looked at the real skills beside it. The loose file is now an
  error of its own and the rest of the root is audited.
- `write-a-skill` described `allowed-tools` as narrowing what a skill may use.
  It grants; the skill now says so and shows a scoped Bash rule.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.

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
