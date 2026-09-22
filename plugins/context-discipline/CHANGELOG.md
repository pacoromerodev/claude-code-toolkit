# Changelog

All notable changes to `context-discipline`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Added
- `check_claude_md.py` reports a rule a hook could enforce — a prohibition
  about pushing, committing, deleting, deploying and the like — as a note with
  what to do about it: CLAUDE.md asks, a `PreToolUse` hook that exits 2
  refuses. It also warns when every emphasised rule sits in the middle of a
  long file, where instructions go quiet, rather than at the ends.
- `claude-md-doctor` says the two things that come before any rewriting: move
  what must never be broken into a hook, and start with no CLAUDE.md at all,
  adding a line only when the same correction repeats.

### Fixed
- The `no-alternative` rule accepts an alternative given in the next sentence
  ("Never push to main. Open a pull request."), which it used to miss because
  it skipped the first four words after the prohibition.


### Changed
- The `/handoff` note is read live at restore time, attributed to the
  assistant with its date, rather than frozen into the snapshot and labelled
  as outranking everything measured. Output is capped at 8,000 characters,
  with the note first, so nothing is silently dropped into a file.

### Fixed
- `not-fired` eval grader states what a correct answer looks like, not only
  what scores badly.
- `restore_state` only restores the snapshot of the session that was compacted,
  and only through SessionStart with the `compact` matcher. It used to fall
  back to any recent snapshot, and to label whatever it found as "restored
  after compaction" even at a fresh session start.
  The PostCompact registration is gone: that event has no way to add context.
  A snapshot of a directory that is not a git repository says so instead of
  reporting a clean tree, and "before compaction compaction" is fixed.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.
- The snapshot is written to the plugin's data directory, keyed by repository,
  instead of `.claude/state/` inside the repository. A state file committed to
  a repository is no longer read back: it could have been written by anyone,
  and a fresh clone makes it look current.

## [0.1.0] — 2026-09-20

### Added
- `save_state` PreCompact hook: snapshots the branch, uncommitted and staged
  files, diffstat, recent commits and stashes to
  `.claude/state/<session_id>.md` before compaction discards the particulars.
  Namespaced by session so two sessions in one repo do not overwrite each
  other.
- `restore_state` hook on PostCompact and SessionStart: hands the snapshot back
  through `hookSpecificOutput.additionalContext`, with a caveat that the tree
  may have moved. Silent when there is no snapshot; declines to restore one
  older than 24 hours, mentioning it instead.
- `scope-task` skill: Explore → Plan → Code → Commit, with the four signals
  that mean the plan no longer matches the work.
- `claude-md-doctor` skill + `scripts/check_claude_md.py`: finds length past
  the point rules get skipped, emphasis inflation, vague standards,
  prohibitions with no alternative, broken and oversized imports, and
  paragraphs that read as background.
- `/handoff` writes the reasoning that cannot be recovered by looking;
  `/context` reports what is filling the context and what to do about it.
- 20 fixture assertions, including the save → restore cycle end to end in a
  throwaway repository.

### Notes
- Built on `PostCompact`, which in Claude Code 2.1 exists and receives the
  compaction summary. The roadmap had assumed it did not and that `SessionStart`
  with a `compact` matcher was needed; the embedded hook documentation says
  otherwise. `SessionStart` is still registered, for a different loss: a resumed
  or fresh session, where nothing carried over at all.
