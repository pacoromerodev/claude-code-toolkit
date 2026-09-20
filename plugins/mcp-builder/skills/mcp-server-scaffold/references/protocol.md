# MCP protocol details

Read this when implementing a client, or when a connection misbehaves. Writing
a server needs none of it.

## The handshake

Three messages, in order:

1. **Initialize Request** — client to server: protocol version, capabilities
2. **Initialize Result** — server to client: its version and capabilities
3. **Initialized Notification** — client to server: ready

A notification has no response. Getting this wrong produces a connection that
appears open and answers nothing.

## Message types

Request–result pairs (`ListToolsRequest` / `ListToolsResult`,
`CallToolRequest` / `CallToolResult`, `ReadResourceRequest` /
`ReadResourceResult`) and one-way notifications. The specification is written
in TypeScript, which is worth knowing when the Python types look surprising.

## Sampling — the server asks the client for a completion

```python
result = await ctx.session.create_message(
    messages=[...], max_tokens=1000,
)
```

The **client** implements `sampling_callback`, runs the model, and pays for the
tokens. This is what lets a server use an LLM without holding a key.

The formats differ between MCP's message types and the model API's, so the
callback has to convert in both directions. A client that does not implement
the callback makes every sampling call fail.

## Logging and progress

Server side:

```python
await ctx.info("message")      # also debug, warning, error
await ctx.report_progress(30, 100)
```

Client side: `logging_callback` on `ClientSession`, and `progress_callback`
passed to `call_tool`. Without them, the messages are sent and dropped.

## Roots — and the part the SDK does not do

Roots are `file://` URIs telling the server which directories it may touch.
The server asks with `list_roots()`; the client answers through a callback.

**The SDK does not enforce them.** Receiving the list is all it does — every
check is yours to write. A server that requests roots and then opens any path
it is given has a path traversal bug, not a configuration problem.

## Transports

**stdio** — the client launches the server as a subprocess and talks over
stdin/stdout. Same machine, one client, no network. The default for a local
tool.

**StreamableHTTP** — HTTP with SSE for server-to-client messages. A session id
travels in the `mcp-session-id` header. The primary SSE stream carries
server-initiated requests and progress; each tool call gets its own stream for
its logs and result.

**`stateless_http=True`** — no session ids, so any instance can answer any
request and the server scales behind a load balancer. The cost: server-to-
client requests stop working, which means **sampling, progress and
subscriptions are gone**. They fail quietly.

**`json_response=True`** — plain JSON responses, no streaming.
