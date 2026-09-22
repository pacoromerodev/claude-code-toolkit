---
type: llm
weight: 1
---

"Some customers" and "whatever is causing it" is a search, not a task. The
symptom has no reproduction, no failing example, no error, and the proposed
scope is a whole subsystem — which is how a session spends its context reading
files and arrives at a guess.

Score well when the response:
- Does not start reading the payment code and proposing fixes
- Asks for what makes the task decidable: a failing example, the error or
  status returned, what "some customers" have in common, what changed on
  Tuesday
- Proposes a first step that produces evidence — reproduce one failure, read
  the logs for a known case — rather than a fix
- Offers a bounded plan to agree before touching code

Score badly when the response:
- Starts a broad exploration of the payment code
- Proposes candidate fixes from the description alone
- Asks one clarifying question and then proceeds anyway
