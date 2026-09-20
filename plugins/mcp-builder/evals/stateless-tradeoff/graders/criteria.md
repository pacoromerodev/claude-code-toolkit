---
type: llm
weight: 1
---

The server uses `report_progress`, `ctx.info` and `ctx.session.create_message`
— progress, logging and sampling. All three are server-to-client messages, and
all three stop working under `stateless_http=True`, without raising.

Score well when the response:
- Names the conflict before recommending stateless mode
- Lists which specific features break, pointing at the calls in this file
- Stresses that they fail **silently** rather than erroring
- Offers the real choice: StreamableHTTP with sticky sessions at the load
  balancer keeps the features; stateless scales freely and loses them
- Mentions that sampling in particular has no workaround in stateless mode

Score badly when the response:
- Recommends `stateless_http=True` as the answer with no caveat
- Discusses load balancers and replicas without reading what the server uses
- Claims the features keep working
