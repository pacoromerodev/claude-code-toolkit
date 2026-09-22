---
name: choose-transport
description: Chooses between stdio, StreamableHTTP and stateless HTTP for an MCP server, and names what each choice gives up. Use when deciding how to run or deploy an MCP server, when a server needs to scale behind a load balancer, or when sampling, progress reporting or subscriptions have stopped working.
allowed-tools: Read, Glob, Grep
---

# Choosing a transport

Three options, and the third one takes features away without telling you.

## The decision

| | stdio | StreamableHTTP | stateless HTTP |
|---|---|---|---|
| How it runs | Client launches it as a subprocess | A server you deploy | A server behind a load balancer |
| Reach | Same machine only | Network | Network |
| Clients | One, its parent | Many | Many |
| Session ids | Implicit | `mcp-session-id` header | **None** |
| Server → client requests | Yes | Yes | **No** |
| Sampling | Yes | Yes | **No** |
| List Roots | Yes | Yes | **No** |
| Elicitation | Yes | Yes | **No** |
| Subscriptions | Yes | Yes | **No** |
| Progress and logs during a call | Yes | Yes | Yes, unless `json_response` |
| Scales horizontally | n/a | With sticky sessions | Freely |

**Start with stdio.** A local tool, a single user, no deployment. It is the
default for a reason: nothing to host, nothing to secure, no session handling.

**Move to StreamableHTTP** when the server must be reachable over a network or
shared by several clients. Sessions are carried in the `mcp-session-id` header,
which means a load balancer in front of it needs sticky sessions.

**Reach for `stateless_http=True` only** when horizontal scaling is a real
requirement and you have checked the list below.

## What stateless mode removes

Each request gets a fresh transport, so there is no session and no way for the
server to open a request of its own to the client. What goes:

- **Sampling** — the server cannot ask the client for a completion
- **List Roots** — it cannot ask which directories it may touch either, which
  is the same call a boundary check depends on
- **Elicitation** — no asking the user anything mid-call
- **Subscriptions** — no resource-change notifications

These are server-to-client *requests*: without a session there is nowhere for
the client's answer to land, so the SDK refuses them rather than hanging.

**Progress and log notifications are a different case**, and this is the part
worth getting right: they travel on the response stream of the call that
produced them, which still exists in stateless mode. `report_progress` and
`ctx.info` keep working. It is `json_response=True` that ends them — that mode
answers a POST with one JSON body, so there is no stream to carry anything
before the result, and the notifications are dropped.

The gain is real: no initialisation handshake per session, and any instance can
answer any request.

```python
mcp = FastMCP("service", stateless_http=True)
```

## Before switching to stateless

Search the server for what would break:

```bash
grep -rn "create_message\|list_roots\|elicit\|subscribe" .
```

Any hit is a server-to-client request, and stateless mode ends it. Either drop
the feature or stay stateful. A `list_roots` hit is the one to look at
hardest: a server that asked for its boundaries and now cannot is a server
with no boundaries.

If you are also setting `json_response=True`, widen the search:

```bash
grep -rn "report_progress\|ctx\.info\|ctx\.debug\|ctx\.warning" .
```

## Deploying StreamableHTTP

- Sticky sessions at the load balancer, or session ids resolve to the wrong
  instance
- Authentication at the edge — MCP does not define one
- The SSE stream is long-lived; idle timeouts on proxies will cut it
- Bound every result regardless of transport: a big payload is expensive
  everywhere
