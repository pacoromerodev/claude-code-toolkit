---
type: llm
weight: 1
---

This is genuinely an agent: what to do with each file depends on what was
found. The question is who runs the loop, and "write it again with better
retries" is the answer that puts hours of work back on a connection staying
up.

Score well when the response:
- Accepts that this is an agent rather than arguing for a workflow
- Lays out the choice: your own loop, the SDK's tool runner, or managed
  agents, and says what each one costs to operate
- Recommends managed agents here, for the reason in the question — a run
  measured in hours that has to be resumable, with the sandbox and the
  progress kept outside the caller's process
- Says what to keep either way: a turn or cost ceiling, tool errors returned
  as errors, and a record of what has already been processed so a resumed run
  does not redo it

Score badly when the response:
- Helps write the hand-rolled loop with retries, as asked, without offering
  the alternatives
- Names the tool runner as the fix for resumption, which it is not: it drives
  the loop in your process, and the process is what died
- Treats the choice as a matter of taste, or answers with a general list of
  agent best practices
