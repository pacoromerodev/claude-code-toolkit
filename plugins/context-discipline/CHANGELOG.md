# Changelog

All notable changes to `context-discipline`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Fixed
- `not-fired` eval grader states what a correct answer looks like, not only
  what scores badly.

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
