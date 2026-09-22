---
name: mcp-server-scaffold
description: Builds an MCP server with the right primitive for each job — tools, resources and prompts — using FastMCP. Use when the user asks to create or extend an MCP server, to expose an API or a database to Claude, or when deciding whether something should be a tool, a resource or a prompt.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_mcp_server.py *)
---

# Building an MCP server

MCP moves the *definition* and the *execution* of a capability out of your
application and into a server anything can connect to. That is the whole point
— and it is what makes it different from tool use, where your own code holds
both.

## Pick the primitive first

This is the decision people get wrong, and it is decided by **who is in
control**:

| Primitive | Controlled by | Use for |
|---|---|---|
| **Tool** | The model | Actions the model decides to take: query, create, send, calculate |
| **Resource** | The application | Context the app attaches: a file, a record, a document the user picked |
| **Prompt** | The user | Templates a person invokes deliberately: a review checklist, a report format |

If the model should decide when it happens, it is a tool. If the application
attaches it, it is a resource. If a person picks it from a menu, it is a
prompt.

Most servers are all tools because tools are the familiar shape. Read-only
context usually wants to be a resource — it does not consume a tool call, and
the application decides when it is relevant.

## A server with all three

```python
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("documents")


@mcp.tool()
async def search_documents(
    query: Annotated[str, Field(description="Free-text search terms")],
    limit: Annotated[int, Field(description="Maximum results", ge=1, le=50)] = 10,
) -> list[dict]:
    """Search the document store by content and return matching documents.

    Use this when you need to find documents but do not know their ids. When
    you already have an id, read the document resource directly instead — it
    is cheaper and returns the full text.

    Returns up to `limit` matches, each with id, title and a short excerpt,
    ordered by relevance. Returns an empty list when nothing matches; raises
    ValueError when the query is empty.
    """
    ...


@mcp.resource("docs://documents", mime_type="application/json")
async def list_documents() -> list[str]:
    """Every document id available in the store."""
    ...


@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
async def read_document(doc_id: str) -> str:
    """The full text of one document."""
    ...


@mcp.prompt()
def summarise_document(doc_id: str) -> list[base.Message]:
    """Summarise a document into three bullets and one risk."""
    return [base.UserMessage(f"Summarise docs://documents/{doc_id} as ...")]
```

Note the resource pair: one **direct** URI for the collection, one **template**
URI with a placeholder for a single item. The placeholders become the
function's arguments.

## The tool description is the tool

A vague description is the most common reason tool use fails. The model is
choosing between your tool and several others, on the strength of this text
alone.

Four things belong in it:

1. **What it does**, concretely
2. **When to use this one** rather than a neighbouring tool — the boundary
3. **What it returns**, including the shape and any truncation
4. **How it fails** — so "no results" can be told apart from "broken"

Put parameter explanations in `Field(description=...)`: that reaches the
schema, where the model reads it. A comment does not.

## Bound every result

One oversized response fills the context window and ends the session. Every
tool that can return a collection takes a `limit`, defaults it sanely, and says
in its description that results are truncated.

## Long work reports progress

```python
@mcp.tool()
async def reindex(ctx: Context) -> str:
    """Rebuild the search index over every document."""
    for done, total in walk():
        await ctx.report_progress(done, total)
        await ctx.info(f"indexed {done}/{total}")
    return "done"
```

Without it the client cannot tell slow from hung.

## Never ask the model for a credential

A parameter called `api_key` is a design error. The model does not hold your
secrets. Read them from the server's own environment.

## Run the Inspector before wiring it to anything

```bash
mcp dev server.py        # opens on ~6274
```

Call each tool, read each resource, render each prompt. A server that works in
the Inspector and fails in a client is a client problem; the reverse is much
harder to diagnose.

Then audit it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_mcp_server.py server.py
```

## Further detail

`references/protocol.md` covers the handshake, message types and the
client-side callbacks — sampling, logging, progress and roots. Read it when
implementing a client or debugging a connection, not to write a server.
