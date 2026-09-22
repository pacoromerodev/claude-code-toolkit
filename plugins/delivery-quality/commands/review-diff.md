---
description: Review the uncommitted diff with the read-only code-reviewer subagent
---

Launch the `code-reviewer` subagent on the current uncommitted change.

$ARGUMENTS

Pass it whatever scope the arguments name — a branch, a directory, a single
file — and default to `git diff HEAD` when nothing is given. Relay its findings
to me in full, including the "Obstacles encountered" section: do not summarise
it away.
