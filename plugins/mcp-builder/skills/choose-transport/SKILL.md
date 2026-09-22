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
| Progress reporting | Yes | Yes | **No** |
| Subscriptions | Yes | Yes | **No** |
| Scales horizontally | n/a | With sticky sessions | Freely |

**Start with stdio.** A local tool, a single user, no deployment. It is the
default for a reason: nothing to host, nothing to secure, no session handling.

**Move to StreamableHTTP** when the server must be reachable over a network or
shared by several clients. Sessions are carried in the `mcp-session-id` header,
which means a load balancer in front of it needs sticky sessions.

**Reach for `stateless_http=True` only** when horizontal scaling is a real
requirement and you have checked the list below.

## What stateless mode removes

Statelessness means no session, and without a session the server cannot send
anything to the client on its own initiative. Everything built on that stops:

- **Sampling** — the server can no longer ask the client for a completion
- **Progress reporting** — `report_progress` has nowhere to go
- **Subscriptions** — no resource change notifications
- **Logging callbacks** — the same problem

These do not raise. They quietly do nothing, which is why this is worth
deciding on purpose rather than discovering later.

The gain is real: no initialisation handshake per session, and any instance can
answer any request.

```python
mcp = FastMCP("service", stateless_http=True)
```

`json_response=True` is a separate switch: plain JSON instead of streaming. It
composes with either mode and costs only incremental delivery.

## Before switching to stateless

Search the server for what would break:

```bash
grep -rn "create_message\|report_progress\|subscribe\|ctx\.info" .
```

Any hit is a feature that stops working. Either drop it, or stay stateful.

## Deploying StreamableHTTP

- Sticky sessions at the load balancer, or session ids resolve to the wrong
  instance
- Authentication at the edge — MCP does not define one
- The SSE stream is long-lived; idle timeouts on proxies will cut it
- Bound every result regardless of transport: a big payload is expensive
  everywhere
