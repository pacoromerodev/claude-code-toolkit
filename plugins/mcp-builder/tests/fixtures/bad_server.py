"""A server with one planted fault per tool."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bad", stateless_http=True)


@mcp.tool()
async def process(data):
    """A helper utility."""
    return data


@mcp.tool()
async def search_records(query: str) -> list:
    """Searches records."""
    return []


@mcp.tool()
async def fetch_remote(url: str, api_key: str) -> str:
    """Fetch a remote document using the given credentials, returning its body.

    Use when the user asks for the contents of a URL. Returns the response
    body as text, or raises on a non-200 status.
    """
    return ""


@mcp.tool()
async def read_file(path: str) -> str:
    """Read a file from disk and return its contents as text.

    Use when the user names a file they want to see. Returns the text, and
    raises FileNotFoundError when it is missing.
    """
    with open(path) as handle:
        return handle.read()


@mcp.tool()
async def reindex_everything() -> str:
    """Rebuild the whole search index across every stored document.

    Use when documents were added outside the normal ingest path. Returns a
    summary line; raises RuntimeError if the store is unreachable.
    """
    for _ in range(1000):
        pass
    return "done"


@mcp.resource("files://secret?token=abc123")
async def leaky() -> str:
    """The configured file listing for the current workspace."""
    return ""
