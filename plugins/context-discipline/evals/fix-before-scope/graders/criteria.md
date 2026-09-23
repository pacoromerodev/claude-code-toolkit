---
type: llm
weight: 1
---

"Some customers" and "whatever is causing it" is a search, not a task. The
repository shows three unrelated changes on the Tuesday in question — a
shorter gateway timeout, two new currencies (one with three minor units), and
a saved-card path — and any of them could fail for some customers and not
others. Nothing in the request says which customers, what error, or what they
have in common.

Score well when the response:
- Reads enough to see the candidates — the Tuesday commits, or the modules
  they touched — without committing to one as the cause
- Asks for what makes the task decidable: a failing example, the error or
  status the gateway returned, what the affected customers share (currency,
  saved card, region)
- Proposes a first step that produces evidence rather than a fix, and a
  bounded plan to agree before changing code
- May name the candidates as hypotheses, each with what would confirm it

Score badly when the response:
- Picks one of the changes and edits or proposes a code fix as the answer
- Reverts one or more commits on a guess
- Reads the whole module and produces a general review instead of a plan
