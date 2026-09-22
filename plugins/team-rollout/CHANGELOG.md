# Changelog

All notable changes to `team-rollout`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Added
- `check_settings.py` checks the marketplace allowlist itself: a
  `strictKnownMarketplaces` that is not an array, an entry that is not a source
  object, an unknown source type, an empty list (reported as the lockdown it
  is), the non-existent `knownMarketplaces` key, and a git marketplace
  registered with no `ref`.

### Changed
- `settings-review` reports a literal credential first — the file is shared,
  so the key is leaked and must be rotated — then grants wider than intended.
  It now also carries what each marketplace key actually does, and which of
  them is managed-only.

### Fixed
- Both shipped templates were rejected by Claude Code's own schema, so a
  policy that read as restrictive applied nothing: `strictKnownMarketplaces`
  was a boolean where an array belongs, `knownMarketplaces` is not a setting,
  and a `$comment` sat inside `hooks`, which takes event names only. CI now
  validates every shipped settings file against the published schema.
- `not-fired` eval grader says what a correct answer looks like; it had failed
  a correct Shift+Tab answer.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.

## [0.1.0] — 2026-09-20

### Added
- `plan-rollout` skill: the five decisions in the order that stops them being
  redone — Structure and Identity, Access, Governance, Spend, Visibility —
  with the four that are hard to undo called out, the additive group rule and
  its consequence for anything regulated, and what actually happens at a spend
  limit.
- `settings-review` skill + `scripts/check_settings.py`: blanket allows,
  bypass as a default mode, literal credentials, unpinned marketplaces,
  relative hook paths, missing timeouts on blocking events, and settings files
  that cannot be parsed — which Claude Code ignores silently.
- `settings/managed-settings.json` and `settings/project-settings.json`:
  reference files with every choice commented.
- `/rollout-plan` and `/settings-check` commands.
- 22 fixture assertions, including that the shipped templates pass the
  checker this plugin ships.
