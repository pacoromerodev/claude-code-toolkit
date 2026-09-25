# Changelog

All notable changes to `delivery-quality`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Removed
- The command files that only restated their skill with defaults attached. A
  command's description is always-on context and the skill's is what the model
  matches on, so a wrapper paid twice for one component. What the wrappers
  added is now in the skill bodies, where it applies whether the skill was
  typed or fired on its own. `/verify`; the skill answers to
  `/delivery-quality:verify-changes`. The command that launches the subagent
  stays, as `/review-diff`.
- Dead MultiEdit branch and its fixture: no such tool exists in Claude Code 2.1,
  and the fixture sent a payload the Edit tool does not produce.

### Added
- `verify-changes` checks that a dependency the change introduces actually
  resolves, against the lockfile or the registry, and says which it checked.
  A package name that looks right is not a package that exists, and a
  plausible unclaimed name is also how a dependency gets taken over later.
- `code-reviewer` checks the change against stated acceptance criteria when
  the task, issue or pull request has them, by name, and reports the ones it
  could not check. A passing suite is not evidence for a criterion nobody
  implemented: the tests came from the same reading of the task.
- `guard_secrets` can redact instead of blocking, per project, behind
  `.claude/secret-guard-redact`. A shell command carrying a secret comes back
  with the value replaced by a placeholder and goes to the user to confirm,
  through `updatedInput` — which replaces the tool's input outright, so every
  other field is returned with it. Shell only: a file written with a
  placeholder in place of a value is a silent corruption. The marker is a
  guard file, so the model cannot enable this for itself.
- `verify-changes` checks a workflow change as what it is: code that runs with
  nobody watching. When the diff touches `.github/workflows/`, it reports on
  the declared permissions, whether checkout keeps the token, anything
  interpolated into a shell, unpinned versions, and — for a job that runs
  Claude — a turn cap, narrow tool grants and no permission bypass.

### Changed
- `/review-diff` says when to use it. Its description named only what it
  launches, so a plain "review the uncommitted changes" was often answered in
  the main thread, as loose prose without the code-reviewer's Blocking /
  Worth fixing / Noted structure: in `review-format`, every run that went
  through `/review-diff` passed and every run that did not failed.
- The `guard-blocks-destructive` eval gives the go-ahead to rewrite and push
  up front. Without it the model stopped to ask before the push, which is
  right, and the guard was never reached — the case failed for a reason that
  had nothing to do with the guard.
- `code-reviewer` no longer claims "before a commit", which had it competing
  with `verify-changes` on every pre-commit prompt. It now says what it is
  for — a second opinion on a change about to be shared — and that it does not
  run the tests.
- `/review` is now `/review-diff`. Claude Code documents `review` as a bundled
  alias of its own `code-review`, so the short form was a coin toss — and the
  two do different jobs: the built-in reviews a pull request, this one launches
  a read-only subagent on the working diff.
- `--force-with-lease` to a protected branch is now blocked too: it only
  guards against unfetched work, and still rewrites shared history.
  Deleting a protected remote branch and `git push --mirror` are blocked.
  Allow rules exempt only the command they match, not a whole chained line.
  Block messages are written for the model and name what to do instead.
- A failing suite comes back as Stop `additionalContext` rather than exit 2:
  the turn continues as hook feedback, not a hook error, bounded by Claude
  Code's own 8-continuation cap. The gate no longer skips its own re-entry,
  so the run after a failure is what checks the fix. Output is clipped to 300
  characters per line and 4,000 in total.

### Fixed
- The test gate no longer traps a turn whose right answer is a failing report.
  It blocked on every stop while the suite was red, so a request to *verify* a
  change — where reporting the failure is the whole job — turned into Claude
  asking the user for permission to finish and explaining how to disable the
  hook. It now re-runs on re-entry, so the fix it demanded is still checked,
  but blocks only once: a second red run ends the turn with a `systemMessage`.
  The block itself now says that a verification should report the failure and
  stop. Measured: `verify-project-command` scored 0.00 against a 0.67 no-plugin
  baseline, three judges, three runs.
- `review-format` and `verify-not-fired` evals had no fixture and could never
  pass; both are now `case.yaml` cases with a scaffold.
- `reset --hard` and `checkout .` were blocked by untracked files, which they
  do not touch. `git clean -n` (a dry run) was blocked. A heredoc written to a
  file and a quoted commit message were read as commands.
- A shell command that only reads or searches (grep, rg, git log -S) and
  writes nothing is no longer scanned for secrets: searching for a leaked key
  was blocked. `.env.example` and its siblings are no longer blocked by name.
  A URL with a port and an at-sign in its path is no longer read as a
  connection string with a password.
- `test_gate` parsed `CLAUDE_TEST_GATE_TIMEOUT` at import time, so a value
  like `15m` took the hook down with a traceback. A project timeout longer
  than the hook's own 960s is now clamped: the harness would have cut the run
  off before the feedback was printed.
  `only_when_changed` counts work already committed on the branch, not just
  the working tree, so committing mid-session no longer skips the gate.
  An enabled gate that cannot run (no runner, unreadable config) says so
  through `systemMessage` instead of writing to a channel only the debug log
  sees.
- All three hooks take the project from the payload's `cwd`, which follows
  Claude into a worktree and after `cd`, instead of `CLAUDE_PROJECT_DIR`,
  which stays where the session started. In a worktree the gate used to test
  the other checkout and pass a real regression, and the destructive guard
  read the wrong `git status`.

### Security
- `guard_destructive` parses the command instead of matching one pattern
  against it. The first version caught one spelling of each threat: a
  force-push with `--force` first, `-f` or `+main`, `rm -Rf`, flags after the
  target, `$HOME` targets, chained, `sudo`, `bash -c` and `$(…)` forms, `DROP`
  followed by `2>/dev/null`, and `kubectl delete --all` all passed.
- `guard_secrets` scans `new_source`, so a NotebookEdit carrying a key is
  blocked; the hook also runs on PowerShell. Writing either guard's
  `.claude/*-guard-allow` file is blocked: switching a guard off is the
  user's decision, and the block message no longer points the model at it.
  Redirect targets are read properly, including `>|` and the real
  destination of install, cp and mv, and Windows path separators count.

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
