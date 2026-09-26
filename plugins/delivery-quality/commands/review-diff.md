---
description: Review uncommitted changes, a branch or named files with the read-only code-reviewer subagent, and relay its Blocking / Worth fixing / Noted report. Use when the user asks to review, look over or check a change, wants a second opinion on it, or is about to commit or share it.
---

Launch the `code-reviewer` subagent on the current uncommitted change.

$ARGUMENTS

Pass it whatever scope the arguments name — a branch, a directory, a single
file — and default to `git diff HEAD` when nothing is given. Relay its findings
to me in full, including the "Obstacles encountered" section: do not summarise
it away.
