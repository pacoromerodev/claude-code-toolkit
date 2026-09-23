---
type: llm
weight: 1
---

It can, and that is the problem: everything a skill reads stays in the
conversation, so an investigation that opens fifty files leaves fifty files'
worth of context behind for a list of five. That work belongs in a subagent,
which returns only its summary — with a skill as the front door if it should
start on its own.

Score well when the response:
- Says the reading is the issue, not the ability: a skill runs in this
  conversation and everything it reads stays
- Recommends a subagent for the investigation, because only the summary
  returns
- Describes what makes the subagent work: a fixed output format, read-only
  tools, and a section for what it could not check
- Explains how the two compose — a skill whose description fires and
  delegates, or a `skills:` preload — rather than presenting them as
  alternatives

Score badly when the response:
- Writes the skill as asked, with no mention of what it costs in context
- Says a skill cannot open files
- Recommends a subagent but says nothing about the output format
