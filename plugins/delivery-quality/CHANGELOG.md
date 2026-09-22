# Changelog

All notable changes to `delivery-quality`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Fixed
- `review-format` and `verify-not-fired` evals had no fixture and could never
  pass; both are now `case.yaml` cases with a scaffold.

## [0.2.0] — 2026-09-20

### Added
- `guard_destructive` PreToolUse hook: blocks commands whose damage outlives
  the session — force-push to a protected branch, `git reset --hard` over
  uncommitted work, `git clean`, `git branch -D`, deletes outside the project,
  `DROP`/`TRUNCATE` against a database that does not look like a test one,
  `chmod 777`, `mkfs`, bulk `kubectl delete`, `terraform -auto-approve`.
  Relaxable per project via `.claude/destructive-guard-allow`.
- Secret guard covers GCP service-account keys, Azure storage and AD secrets,
  signed JWTs, Basic and Bearer headers, npm, PyPI, SendGrid and Twilio
  tokens, AWS secret access keys, and writes to `.pem`, `.p12`, `.pfx`,
  `.jks` and `.keystore`.
- Secret guard follows shell redirections: `cat > .env`, `tee`, `cp` and `mv`
  into a blocked path are caught the same way a `Write` to it is.
- Per-project allowlist for the secret guard: `.claude/secret-guard-allow`.
- `.claude/test-gate.json` configures the gate: explicit `command`, `timeout`,
  and `only_when_changed` globs so a docs-only session is not gated.
- Fixture suite grown from 21 to 47 cases; fourth eval case covering the
  destructive guard.

### Changed
- The test gate reports the **first** failure with context instead of the last
  60 lines, which on Maven and Gradle is the build summary and says nothing.

### Fixed
- `Authorization: "Basic …"` was missed whenever quotes sat between the header
  name and the value, which is how it appears in JSON and YAML.
- The destructive guard blocked legitimate test databases: `\btest\b` does
  not match `app_test`, and `\blocal\b` does not match `localhost`. Markers
  are matched as substrings now.

## [0.1.1] — 2026-09-20

### Fixed
- The secret guard let a real password through in a connection string pointing
  at a reserved documentation domain: the lowercase `example` in
  `cluster0.example.net` matched the allowlist. Word markers are now
  case-sensitive, matching the uppercase convention placeholders actually use
  — including AWS's own `AKIAIOSFODNN7EXAMPLE`. Found by the fixture suite.

### Added
- Fixture suite: 21 payload cases covering blocked secrets, blocked paths,
  legitimate values that must pass, and malformed input that must fail open.
- Eval suite: three cases covering the skill firing on a green-but-broken
  change, staying quiet on an unrelated question, and the review output format.

## [0.1.0] — 2026-09-20

### Added
- `verify-changes` skill: runs the tests, reads the diff, and checks that no
  test was weakened, skipped or deleted to make the suite pass.
- `code-reviewer` subagent: read-only review with a fixed output format and a
  required "Obstacles encountered" section.
- `guard_secrets` PreToolUse hook: blocks writes that would put a real
  credential on disk.
- `test_gate` Stop hook: opt-in per project, refuses to end a session while
  the suite fails.
- `/verify` and `/review` commands.
