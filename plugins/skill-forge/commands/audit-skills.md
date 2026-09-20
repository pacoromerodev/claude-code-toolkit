---
description: Audit a skills directory for the faults that stop skills firing
---

Audit skills using the `audit-skills` skill.

$ARGUMENTS

Default to `.claude/skills` when no path is given, and also check
`~/.claude/skills` if it exists. Report errors first, then warnings grouped by
skill, each with the fix rather than a restatement of the problem.
