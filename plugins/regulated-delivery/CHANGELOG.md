# Changelog

All notable changes to `regulated-delivery`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-09-29

### Added
- `guard_pii`, a `PreToolUse` hook on `Write`, `Edit`, `MultiEdit` and
  `NotebookEdit`. It blocks an IBAN, a card number, a DNI or a NIE that
  passes its issuer's check: the ISO 13616 length and mod-97 check, a scheme
  prefix plus Luhn, or the control letter. Published test values pass, and a
  project can allow more in `.claude/pii-guard-allow`, which the guard
  blocks the agent from writing. The block message masks the value.
- Thirteen fixture cases, and two eval cases: `guard-blocks-pii` and the
  negative `not-fired`. Neither has been measured yet.
