---
name: scope-task
description: Breaks a large or vague request into an explored, agreed plan before any code is written, and turns a reported symptom into evidence before a fix. Use when a request touches several files or systems, when it is open-ended or underspecified, when the user asks to refactor or migrate something, when a bug is reported with no failing example and the fix would be a search, or when work has started and it is not clear what "done" looks like.
allowed-tools: Read, Glob, Grep, TodoWrite
---

# Scoping work before writing it

Context is working memory, and a vague prompt spends more of it than a precise
one — the exploration goes wider, more files get read, more of it turns out to
be irrelevant. The cost of scoping is paid once. The cost of not scoping is
paid on every turn afterwards.

## Explore → Plan → Code → Commit

### 1. Explore

Read before writing. Find the files that matter, the existing conventions, the
tests that cover the area, and the callers of anything about to change.

Prefer a subagent for the wide sweep: it reads forty files and returns the
conclusion, and the forty files never enter this context. Use the main thread
when the intermediate detail is what you need.

Finish this step able to answer: which files change, what currently depends on
them, and what could break that nobody has mentioned.

**A reported symptom is not a task yet.** "Payments fail for some customers
since Tuesday, find it and fix it" names no failing case, no error, and
nothing the affected users share. Reading the whole subsystem to guess is how
a session is spent arriving at a plausible wrong answer — and the guess is
expensive to disprove afterwards, because it has already been written.

Get one piece of evidence before any hypothesis:

- A single failing example: the input, the response, the time it happened
- What the failures have in common — a currency, a plan, a region, a route
- What changed around when it started, as candidates rather than as a verdict

Then say which candidate each piece of evidence would rule in or out, and ask
for the one thing that separates them. If nothing is available, say so and
scope the smallest step that produces it, rather than the fix.

### 2. Plan

State it before writing code, and make it checkable:

- What changes, file by file
- What stays the same, especially any public contract
- What **done** means — the condition you will verify, not a feeling
- What you are deliberately not doing

Then stop and get agreement. A plan rejected in thirty seconds is cheaper than
an implementation rejected in thirty minutes, and this is the moment where a
wrong assumption costs nothing to fix.

For anything long-running, set the goal as a verifiable condition: "the suite
passes and no test was weakened", not "improve the tests".

### 3. Code

Follow the plan. When something forces a change to it, say so and say why —
silently taking a different route is how a session ends somewhere nobody
intended.

Track multi-step work in a todo list. It survives compaction better than
narrative does, and it makes the remaining work visible to the user rather than
implied.

### 4. Commit

Small, coherent commits. The message says **why**, since the diff already says
what. Verify before committing, not after.

## Managing the context you have

- **`/context`** shows what is being spent. Look at it when responses start
  drifting or the model repeats itself.
- **`/compact <instructions>`** with instructions beats bare `/compact` — say
  what to keep: "keep the migration plan and the failing test, drop the file
  listings".
- **`/clear`** between unrelated tasks. Carrying the previous task's context
  into a new one costs on every turn and helps with none of them.
- **Double Esc** rewinds. Restoring code, conversation or both is often better
  than arguing a session back onto the rails.

## When to stop and re-scope

Any of these means the plan no longer matches the work:

- The third unexpected file has to change
- A test that should be unrelated starts failing
- The same fix has been attempted twice in different ways
- You cannot say what "done" means any more

Stop, say what changed, and re-plan. Continuing from a broken plan spends
context to end up further from the goal.
