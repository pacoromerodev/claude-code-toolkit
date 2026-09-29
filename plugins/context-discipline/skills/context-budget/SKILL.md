---
name: context-budget
description: Read the numbers from /context and say what to do next
argument-hint: "[what you are about to do next]"
disable-model-invocation: true
---

Decide what this session should do about its context.

$ARGUMENTS

**You cannot measure the context from inside it.** There is no tool that
returns how full the window is, and an estimate stated as a number is a guess
the user will act on. Claude Code's own `/context` prints the breakdown: ask
for that output, or work from what is observable here — how long the session
has run, how much was read, whether the same ground is being covered twice.

Then say which of these applies, and why:

- **Keep going** — there is room, the work is coherent
- **`/compact` with instructions** — name what to keep and what to drop, never
  a bare compact
- **`/clear`** — this task is finished and the next one is unrelated
- **Rewind (double Esc)** — the session went somewhere unintended, and arguing
  it back will cost more than restarting from the good point
- **`/handoff` then `/clear`** — the work continues but this session has
  accumulated too much to be worth carrying

Name the evidence: what is actually taking up room, and whether responses have
started drifting or repeating.
