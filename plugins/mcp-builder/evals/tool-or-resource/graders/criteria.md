---
type: llm
weight: 1
---

A mode parameter makes one vague tool out of three clear ones, which is
the opposite of the fix. The question is which primitive each capability is:
a search is a tool the model chooses, a document by id is a resource the
application attaches, and a summary instruction is a prompt the user picks.

Score well when the response:
- Rejects the mode parameter, and says why: a tool chosen by description
  becomes harder to choose when it does several things
- Separates the three by who controls them — the model calls a tool, the
  application attaches a resource, the user selects a prompt
- Says `get_doc` by identifier is a resource rather than a tool, and what
  changes when it is one
- Addresses the symptom: the descriptions decide whether the others are ever
  called, and says what a good one contains

Score badly when the response:
- Agrees with the merge
- Keeps all three as tools with no discussion of the primitives
- Recommends prompt engineering in the client as the fix
