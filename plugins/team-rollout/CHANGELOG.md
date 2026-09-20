# Changelog

All notable changes to `team-rollout`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

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
