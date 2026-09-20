#!/usr/bin/env bash
set -euo pipefail
cat > server.py <<'PY'
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("inventory")


@mcp.tool()
async def get_data(id: str) -> dict:
    """Gets data."""
    return {}


@mcp.tool()
async def lookup(query: str) -> list:
    """A helper for lookups."""
    return []


@mcp.tool()
async def check(sku: str) -> bool:
    """Checks a thing."""
    return True
PY
