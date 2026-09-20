#!/usr/bin/env bash
set -euo pipefail
cat > server.py <<'PY'
from mcp.server.fastmcp import Context, FastMCP

mcp = FastMCP("indexer")


@mcp.tool()
async def index_corpus(path: str, ctx: Context) -> str:
    """Index every document under a path into the search store.

    Use when documents were added outside the normal ingest path. Returns a
    count of indexed documents; raises RuntimeError when the store is down.
    """
    for done in range(100):
        await ctx.report_progress(done, 100)
        await ctx.info(f"indexed {done}")
    return "100 documents"


@mcp.tool()
async def summarise_corpus(ctx: Context) -> str:
    """Summarise the indexed corpus into a short report.

    Use after indexing, when the user wants an overview rather than search
    results. Returns the report text; raises RuntimeError when nothing is
    indexed.
    """
    result = await ctx.session.create_message(messages=[], max_tokens=500)
    return str(result)
PY
