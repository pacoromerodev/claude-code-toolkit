---
type: llm
weight: 1
---

Two one-word descriptions and two unexplained parameters. Nothing in them
says what either tool is for, what `q` or `id` mean, or when one is a better
choice than the other, so the model picks by name. A system-prompt rule papers
over it and stops applying the moment a third tool arrives.

Score well when the response:
- Says the descriptions are the cause, not the routing, and that a
  system-prompt rule is the wrong layer
- Rewrites both descriptions, and the rewrite says what each tool does, when
  to use it, what it returns, and how it differs from the other
- Describes the parameters: that `id` is an order identifier in a specific
  form, that `q` is free text
- Says what happens when the id is not found, so the model can tell an empty
  result from an error

Score badly when the response:
- Suggests the system-prompt rule, tool_choice, or reordering the array as
  the fix
- Rewrites only one description
- Returns advice about descriptions without producing the rewritten
  definitions
