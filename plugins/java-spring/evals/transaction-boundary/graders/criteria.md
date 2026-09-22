---
type: llm
weight: 1
---

The boundary belongs where the unit of work is, which is the service
method: a controller boundary keeps a transaction open across HTTP concerns
and serialisation, and a repository boundary makes each call its own
transaction, so two writes in one operation cannot roll back together.

Score well when the response:
- Says the service layer, and defines the reason as the unit of work
- Explains what is wrong with the repository placement: each call commits
  separately, so a multi-step operation has no atomicity
- Explains what is wrong with the controller placement: the transaction spans
  request handling and response rendering, holding a connection longer than
  needed
- May mention that self-invocation bypasses the proxy, or read-only
  transactions for queries

Score badly when the response:
- Recommends the controller
- Says it does not matter, or that it is a matter of team preference
- Recommends annotating everything
