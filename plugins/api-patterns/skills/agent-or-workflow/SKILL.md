---
name: agent-or-workflow
description: Decides whether a task should be a fixed workflow or an agent with tools, and names the pattern to use. Use when designing anything that calls a model more than once, when an agent behaves unpredictably, or when the user asks how to structure an AI feature.
allowed-tools: Read, Glob, Grep
---

# Workflow or agent

**If you know the steps, write a workflow.** It is more precise, cheaper,
testable, and it fails in ways you can reproduce. Reach for an agent when the
steps genuinely cannot be known in advance.

That order matters. Agents are more interesting to build and more expensive to
run, debug and trust, and a great many of them are a workflow that was never
written down.

| | Workflow | Agent |
|---|---|---|
| You know the steps | Yes | No |
| Path | Fixed | Chosen at run time |
| Cost | Predictable | Varies per run |
| Testing | Each step in isolation | End to end, statistically |
| Failure | At a known step | Anywhere, differently each time |

## Workflow patterns

**Chaining** — output of one step feeds the next. For work with genuine stages:
extract, then transform, then format. Each step is separately testable, and
each can use a cheaper model.

**Routing** — classify the input, send it to a specialised prompt. Beats one
prompt that tries to cover everything, because each branch can be tuned without
regressing the others.

**Parallelisation** — independent subtasks at once, results combined. Latency
is the slowest branch instead of the sum.

**Evaluator–optimiser** — one call produces, another critiques against
criteria, the first revises. Use when quality matters more than latency and
"better" can be written down. Cap the iterations.

## When it really is an agent

Give it:

- **Few, abstract tools.** `read`, `write`, `edit`, `glob`, `grep`, `bash` go a
  long way. A tool per API endpoint produces a catalogue nobody can choose
  from.
- **A way to see the environment.** Well-behaved agents spend a large share of
  their calls observing before acting. Without read tools, an agent guesses.
- **Verification.** Tests, a validator, a check it can run itself. An agent
  that cannot tell whether it succeeded will report that it did.
- **A stopping condition.** Maximum turns, a budget, a checkable goal.

## Choosing the model

Evaluate from the cheapest upward, on the same dataset. Start with the small
fast model; move up only where it measurably fails. Route by task rather than
picking one model for everything — extraction and final drafting are different
jobs.

## The honest test

Write down the steps. If you can, that is your workflow. If you get three steps
in and the fourth depends on what the first three found, you have an agent —
and you now know exactly which part needs the freedom, which is usually smaller
than the whole task.
