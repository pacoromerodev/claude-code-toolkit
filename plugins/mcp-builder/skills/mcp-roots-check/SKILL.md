---
name: mcp-roots-check
description: Implements filesystem boundaries in an MCP server, because the SDK reports roots but does not enforce them. Use when a server reads or writes files, when adding path parameters to a tool, or when reviewing a server for path traversal.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_mcp_server.py *)
---

# Roots, and the check the SDK does not do

Roots are `file://` URIs by which the client tells the server which directories
it may touch. The server asks:

```python
roots = await ctx.session.list_roots()
```

**That is all the SDK does.** It delivers the list. It does not check a single
path against it.

So a server that requests roots and then opens whatever path it is handed has
exactly the same path traversal bug as one that never asked. The roots
mechanism is a channel for the boundary, not the enforcement of it.

## The check

```python
from pathlib import Path


def is_path_allowed(candidate: str, roots: list[Path]) -> Path:
    """Resolve `candidate` and confirm it sits inside one of `roots`.

    Raises ValueError otherwise. Always use the returned path — never the
    string that was passed in.
    """
    resolved = Path(candidate).expanduser().resolve()
    for root in roots:
        root = root.expanduser().resolve()
        if resolved == root or root in resolved.parents:
            return resolved
    raise ValueError(f"path outside the allowed roots: {candidate}")
```

Three details that are the whole check:

1. **`.resolve()` first.** It collapses `..` and follows symlinks. Comparing
   unresolved strings is the bug — `/allowed/../../etc/passwd` starts with
   `/allowed`.
2. **Compare resolved to resolved.** A root that is itself a symlink will not
   match otherwise.
3. **Use the returned path.** Validating one string and then opening another
   is how a check gets defeated between the two lines.

`root in resolved.parents` beats `str.startswith`: `/allowed-other` starts with
`/allowed`.

## Wire it into every path-taking tool

```python
@mcp.tool()
async def read_file(path: str, ctx: Context) -> str:
    """Read a UTF-8 text file from within the allowed roots.

    Use when you need the contents of a file the client has granted access to.
    Returns the text; raises ValueError when the path is outside the roots or
    the file does not exist.
    """
    roots = [Path(r.uri.path) for r in (await ctx.session.list_roots()).roots]
    safe = is_path_allowed(path, roots)
    return safe.read_text(encoding="utf-8")
```

No tool takes a path without going through this. One that does not is the one
that will be found.

## When the client sends no roots

Decide deliberately, and say which in the code:

- **Refuse** — safest, and correct for a server whose whole job is file access
- **Fall back to a configured directory** — never to the process's working
  directory, which is wherever the client happened to launch it

Never fall back to "anywhere".

## Beyond paths

The same shape applies to any boundary the client describes and the SDK only
reports: allowed hosts for a fetch tool, allowed tables for a query tool,
allowed topics for a publish tool. Receiving the constraint is not applying it.

## Checking a server

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_mcp_server.py server.py
```

It flags tools that touch the filesystem with no visible path check.
