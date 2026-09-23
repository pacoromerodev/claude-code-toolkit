---
type: llm
weight: 1
---

`read_file` asks the client for its roots and refuses anything outside them.
The server runs with `stateless_http=True`, which ends every server-to-client
request: `list_roots` cannot be answered, so the boundary check cannot run,
and every call fails. "Behind a load balancer last week" is the change that
did it.

Score well when the response:
- Connects the failure to `stateless_http=True` removing `list_roots`
- Explains why: no session, so a request from server to client has nowhere
  for the reply to land
- Gives a real choice — run stateful with sticky sessions and keep the roots
  call, or keep stateless and take the boundary from configuration the server
  already holds, checked the same way
- Does not propose dropping the check, or catching the error and reading the
  file anyway

Score badly when the response:
- Blames the load balancer's networking, timeouts or health checks without
  reaching the transport mode
- Suggests removing the roots check, widening it, or falling back to "allow
  everything" when `list_roots` fails
- Rewrites the path comparison without noticing the roots call never returns
