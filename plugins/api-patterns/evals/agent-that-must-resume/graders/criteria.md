---
type: llm
weight: 1
---

This is genuinely an agent: what to do with each file depends on what was
found. Two things are wrong with "rewrite the loop with better retries": a
retry handles one failed request, not a process that died two hours in with
no record of what it had done; and the question of who runs a multi-hour loop
at all has not been asked.

A durable record of progress is necessary whichever way it goes, so an answer
that says so is right as far as it goes. What separates a complete answer is
the second half.

Score well when the response:
- Says retries do not address the failure, and that the missing piece is a
  durable record of what has been processed, so a resumed run does not redo
  or skip work
- Lays out who can run the loop — your own code, the SDK's tool runner, or
  managed agents — and what each one leaves you operating
- Makes a reasoned recommendation among them for a run measured in hours
  that must survive a dropped connection. Managed agents are the natural fit;
  a self-run loop with checkpointing is acceptable if the answer says what
  that costs to operate
- Says the tool runner does not help with resumption, if it mentions it: it
  drives the loop inside the process that died

Score badly when the response:
- Helps write the retry logic as asked and stops there
- Never considers who runs the loop, only how to make the current one sturdier
- Presents the tool runner as the fix for resumption
- Treats the choice as a matter of taste
