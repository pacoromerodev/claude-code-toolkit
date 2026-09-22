---
type: llm
weight: 1
---

Roots are what the client reports, not a boundary anything enforces. A
tool that opens the path it was handed reads whatever that path resolves to,
and logging the roots at startup does nothing at call time.

Score well when the response:
- Says plainly that the server can read outside the roots: nothing checks
- Explains the difference between the client reporting a boundary and the
  server enforcing one
- Gives the check: resolve the candidate path, resolve the roots, confirm the
  candidate is inside one, and refuse otherwise
- Mentions that resolution must happen before the comparison, so `..` and a
  symlink cannot walk out
- Mentions that roots can change during a session, so a value read at startup
  is stale

Score badly when the response:
- Says the roots are enforced by the protocol or the SDK
- Suggests checking the path with a prefix string comparison and nothing else
- Answers only that the tools should validate input, without saying against
  what
