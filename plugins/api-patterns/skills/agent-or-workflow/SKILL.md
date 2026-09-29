---
name: agent-or-workflow
description: Decides whether a task should be a fixed workflow or an agent with tools, names the pattern, and — for an agent — who should run its loop: your own code, the SDK's tool runner, or managed agents. Use when designing anything that calls a model more than once, when an agent behaves unpredictably or dies partway through a long run, or when the user asks how to structure or operate an AI feature.
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

## Once it is an agent: who runs the loop

Three ways to build the same thing, and they differ in what you operate, not
in what the model does.

| | You write | Reach for it when |
|---|---|---|
| **Your own loop** | Send messages with tools; on a tool-use stop, run each call, append the results, send again; stop on end turn | Something must happen *between* steps: an approval, an audit entry, a rule about which tool may run next |
| **The tool runner** | Your existing functions, handed to the SDK's runner | The standard case. It builds the schemas from your types and docstrings and drives the loop, so there is no `while`, no dispatch on stop reason, and no schema kept in sync by hand |
| **Managed agents** | The task, and the rubric for done | The work runs for minutes or hours, needs a sandbox, files, parallelism, memory across sessions, or resumption after a failure — and you do not want to operate that |

The spectrum is how much of the loop you hand over: you run it, the runner
runs it, or the whole agent runs elsewhere. Start at the middle unless
something in the first column applies; the loop is not where the value is.

Whichever you pick, the bounds are yours: a turn limit, a cost ceiling,
timeouts, and tool errors returned as errors rather than swallowed.

## Choosing the model

Evaluate on the same dataset before choosing. Start with the strongest model
turned down to a lower effort: it often matches a smaller model run harder, and
one model keeps one cache. Move to a smaller model where it measurably holds
the same quality. Route by task rather than picking one model for everything —
extraction and final drafting are different jobs.

## The honest test

Write down the steps. If you can, that is your workflow. If you get three steps
in and the fourth depends on what the first three found, you have an agent —
and you now know exactly which part needs the freedom, which is usually smaller
than the whole task.
