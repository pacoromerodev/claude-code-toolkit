---
type: llm
weight: 1
---

A one-word typo fix, fully specified. The right response fixes it.

Score well when the response:
- Changes "recieve" to "receive" in `README.md` and nothing else
- Reports the change in a line

Score badly if the response explores the codebase, produces a plan, opens a
todo list, or asks what "done" means before changing one word. Scoping a
trivial request is the false positive that makes a planning skill something
users disable.
