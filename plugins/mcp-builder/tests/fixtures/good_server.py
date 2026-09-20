"""A server that gets the shape right."""
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("documents")


def is_path_allowed(candidate: str, roots: list) -> Path:
    """Resolve and confirm the path sits inside one of the allowed roots."""
    resolved = Path(candidate).expanduser().resolve()
    for root in roots:
        root = Path(root).expanduser().resolve()
        if resolved == root or root in resolved.parents:
            return resolved
    raise ValueError("path outside the allowed roots")


@mcp.tool()
async def search_documents(
    query: Annotated[str, Field(description="Free-text search terms")],
    limit: Annotated[int, Field(description="Maximum results", ge=1, le=50)] = 10,
) -> list[dict]:
    """Search the document store by content and return matching documents.

    Use this when you need to find documents but do not know their ids. When
    you already have an id, read the document resource directly instead — it
    is cheaper and returns the full text.

    Returns up to `limit` matches with id, title and excerpt, ordered by
    relevance. Returns an empty list when nothing matches; raises ValueError
    when the query is empty.
    """
    return []


@mcp.tool()
async def read_document_file(
    path: Annotated[str, Field(description="Path within an allowed root")],
    ctx: Context,
) -> str:
    """Read a UTF-8 text file from inside the directories the client allowed.

    Use when the user names a file on disk rather than a stored document id.
    Returns the file text; raises ValueError when the path resolves outside
    the allowed roots, and FileNotFoundError when it does not exist.
    """
    roots = [r.uri.path for r in (await ctx.session.list_roots()).roots]
    safe = is_path_allowed(path, roots)
    return safe.read_text(encoding="utf-8")


@mcp.resource("docs://documents", mime_type="application/json")
async def list_documents() -> list[str]:
    """Every document id currently available in the store."""
    return []


@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
async def read_document(doc_id: str) -> str:
    """The full text of one stored document, by id."""
    return ""


@mcp.prompt()
def summarise(doc_id: str) -> list:
    """Summarise a document into three bullets and one risk."""
    return [base.UserMessage(f"Summarise docs://documents/{doc_id}")]
