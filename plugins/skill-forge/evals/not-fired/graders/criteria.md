---
type: llm
weight: 1
---

This asks for an explanation, not for work on a skill. The right response
answers it: a skill is matched against its description and loads on demand; a
command is typed explicitly.

Score well when the response:
- Makes that distinction: who triggers each, and when its content loads
- May add that a skill can also be invoked by name, as a command is

Score badly if the response scaffolds a skill, audits a directory, or launches
the description subagent. Firing here is a false positive, and the cost lands
on every conceptual question the user asks.
