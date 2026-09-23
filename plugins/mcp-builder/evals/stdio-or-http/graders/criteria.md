---
type: llm
weight: 1
---

Thirty users is not thirty concurrent clients of one process: with stdio,
each person's client launches its own copy, on their machine, with their own
credentials. HTTP is what you reach for when the server must be reachable over
a network or hold something shared — and it brings sessions, authentication
and deployment with it.

Score well when the response:
- Says stdio is not a toy transport, and what actually decides between them:
  whether the server must be reachable over a network or shared
- Points out that each stdio client runs its own process, so the number of
  users is not the constraint
- Names what HTTP adds that must then be handled: session ids, sticky
  sessions behind a load balancer, authentication at the edge, deployment
- Gives a reason that would flip the decision — shared cache or index,
  central credentials, a client that cannot spawn processes

Score badly when the response:
- Agrees that stdio is only for local experiments
- Recommends HTTP with no mention of what it costs to run
- Recommends stateless mode as a default
