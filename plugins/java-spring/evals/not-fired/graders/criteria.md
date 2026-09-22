---
type: llm
weight: 1
---

This is a language question. The right response answers it: checked exceptions
are declared and must be handled or propagated; unchecked ones extend
RuntimeException and need neither.

Score well when the response:
- States that difference correctly, with an example of each if it likes
- Stays an explanation, of a length that fits the question

Score badly if the response applies house conventions, reviews code, starts a
migration review, or produces a checklist. Firing a domain skill on a
conceptual question is a false positive, and the cost lands on every question
the user asks while the plugin is installed.
