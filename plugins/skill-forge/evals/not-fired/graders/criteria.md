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

Score badly if the response scaffolds a skill, runs an audit over a directory,
or launches a subagent. Nothing in this plugin should act on a conceptual
question; if something does, the cost lands on every question like it.
