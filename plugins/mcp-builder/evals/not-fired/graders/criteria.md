---
type: llm
weight: 1
---

A conceptual question. The right answer explains it: with tool use, your own
application holds both the tool definitions and their execution; MCP moves both
into a separate server that any client can connect to, so the capability is
shared rather than rebuilt per application.

Score well when the response:
- Draws that distinction: who defines and runs the tools, and who can reuse them
- Notes that the two are complementary — MCP tools still reach the model
  through tool use

Score badly if the response scaffolds a server, writes files, or runs the
audit script. Building something in answer to "what is the difference" is a
false positive, and an expensive one.
