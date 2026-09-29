---
name: handoff
description: Write a handoff note that survives compaction, a new session, or another person
argument-hint: "[what the next session should focus on]"
disable-model-invocation: true
---

Write `.claude/handoff.md` for whoever picks this up next — a later session, or
someone else.

$ARGUMENTS

Keep it under 40 lines and write only what cannot be recovered by looking:

- **Goal** — what we are trying to achieve, in one sentence
- **Done so far** — what actually works now, not what was attempted
- **Next** — the immediate next step, concretely
- **Decisions** — what was chosen and what was rejected, with the reason. This
  is the part nobody can reconstruct from the diff.
- **Traps** — what looks wrong but is deliberate, and what broke last time

Do not list changed files or restate the diff: `git status` and `git diff` say
that better, and the state snapshot already captures it. Anything measurable is
already covered — write down the reasoning that is not.
