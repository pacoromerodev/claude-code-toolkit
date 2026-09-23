---
type: llm
weight: 1
---

The server uses `report_progress`, `ctx.info` and `ctx.session.create_message`.
Only the last of those is a server-to-client *request*, and it is the one
`stateless_http=True` ends: without a session, the client's reply has nowhere
to land. Progress and log notifications travel on the response stream of the
call that emitted them, which stateless mode still has — `json_response=True`
is what would drop those.

Score well when the response:
- Names `create_message` (sampling) as what breaks, pointing at the call in
  this file, before recommending stateless mode
- Offers the real choice: StreamableHTTP with sticky sessions at the load
  balancer keeps sampling; stateless scales freely and loses it
- Is accurate about progress and logging — either saying they survive
  stateless mode, or not claiming they break

Score badly when the response:
- Recommends `stateless_http=True` as the answer with no caveat
- Says progress and logging stop working under stateless mode, which would
  send someone rewriting code that is fine
- Discusses load balancers and replicas without reading what the server uses
