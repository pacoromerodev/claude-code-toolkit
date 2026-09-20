# mcp-builder

Build MCP servers a model can actually use.

```
/plugin install mcp-builder@pacoromerodev
```

## Components

| Component | Type | Fires when |
|---|---|---|
| `mcp-server-scaffold` | Skill | Creating or extending a server; deciding tool vs resource vs prompt |
| `choose-transport` | Skill | Deciding how to run a server; scaling it; sampling or progress stopped working |
| `mcp-roots-check` | Skill | A server reads or writes files, or takes a path parameter |
| `mcp-review` | Subagent | A server changes, or a tool is never called |
| `/mcp-new`, `/mcp-review` | Commands | Typed |

## Pick the primitive by who is in control

The decision most servers get wrong, because tools are the familiar shape:

| Primitive | Controlled by | For |
|---|---|---|
| **Tool** | The model | Actions it decides to take |
| **Resource** | The application | Context the app attaches |
| **Prompt** | The user | Templates a person invokes |

A server that is all tools usually has resources hiding in it: read-only
context the application should attach, currently costing a tool call each time.

## The description is the tool

A model chooses among tools on the strength of the description alone — that is
the single most common reason a tool is never called. Four things belong in it:
what it does, **when to use this one rather than a neighbouring tool**, what it
returns, and how it fails.

Parameter explanations go in `Field(description=...)`, which reaches the
schema. A comment does not.

## The auditor

```bash
python3 plugins/mcp-builder/scripts/check_mcp_server.py server.py
```

Parses with `ast` rather than grepping.

**Errors:**

| Finding | Why |
|---|---|
| No docstring on a primitive | The model has only the name to go on |
| Untyped parameter | The schema is generated from annotations |
| `api_key` or `token` as a parameter | The model does not hold your secrets |
| Credential in a resource URI | URIs are visible to the client and get logged |
| Filesystem access with no path check | The SDK reports roots and enforces nothing |
| `stateless_http=True` alongside sampling, progress or subscriptions | Those stop working, silently |

**Warnings and notes:** thin descriptions, descriptions with no selection cue,
vague parameter names, collections with no `limit`, long-running tools that
take no `Context`, and a server with tools but no resources.

Resources and prompts are **not** held to the tool-length description rule — a
resource is attached by the application and a prompt is picked from a labelled
list, so one clear sentence is the right length for both.

## Stateless mode takes things away quietly

```python
mcp = FastMCP("service", stateless_http=True)
```

Scales freely behind a load balancer, and removes every server-to-client
message: **sampling, progress reporting, subscriptions and logging callbacks**.
None of them raise. They do nothing.

Before switching:

```bash
grep -rn "create_message\|report_progress\|subscribe\|ctx\.info" .
```

Every hit is a feature that stops working.

## Roots are reported, not enforced

`list_roots()` delivers the boundary. The SDK checks nothing against it, so a
server that asks for roots and then opens the path it was handed has the same
traversal bug as one that never asked.

The check is three details: `.resolve()` first so `..` and symlinks collapse,
compare resolved against resolved, and use the **returned** path — validating
one string and opening another is how a check gets defeated between two lines.

## Tests

```bash
plugins/mcp-builder/tests/run.sh
```

21 assertions. Every planted fault must be found, the good server must come
back silent, the messages must explain the consequence rather than name the
rule, and a purpose-built stateless conflict must be reported as an error
naming both broken features.

## Evals

```bash
claude plugin eval plugins/mcp-builder --scaffold --allow-tools Bash
```

- **tool-never-called** — three tools described in two words each. The
  diagnosis must be the descriptions, and the deliverable must be the rewrites.
- **stateless-tradeoff** — scaling a server that uses progress, logging and
  sampling. The answer must name what stateless mode removes.
- **not-fired** — "what is the difference between MCP and tool use", which must
  not start building a server.

## Requirements

Python 3.8+ on `PATH` for the auditor. Standard library only. The skills assume
the Python MCP SDK with FastMCP.
