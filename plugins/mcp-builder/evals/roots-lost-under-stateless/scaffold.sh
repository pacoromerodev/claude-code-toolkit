#!/usr/bin/env bash
set -euo pipefail
cat > server.py <<'PY'
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

mcp = FastMCP("files", stateless_http=True)


@mcp.tool()
async def read_file(path: str, ctx: Context) -> str:
    """Read a text file the client has granted access to.

    Use when the user asks for the contents of a file. Returns the text;
    raises ValueError when the path sits outside the granted directories.
    """
    result = await ctx.session.list_roots()
    roots = [Path(root.uri.path).resolve() for root in result.roots]
    candidate = Path(path).resolve()
    for root in roots:
        if candidate == root or root in candidate.parents:
            return candidate.read_text(encoding="utf-8")
    raise ValueError(f"path outside the allowed roots: {path}")
PY
