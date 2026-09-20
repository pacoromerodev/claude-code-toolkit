---
type: llm
weight: 1
---

Three tools — `get_data`, `lookup`, `check` — with descriptions of two or three
words each: "Gets data.", "A helper for lookups.", "Checks a thing." The model
chooses a tool by reading its description, so with these it has nothing to go
on and answers from memory instead. Nothing else about the file is broken.

Score well when the response:
- Names the descriptions as the cause, not the wiring, the transport or the
  client configuration
- Explains that the model selects among tools on the description alone
- Supplies rewritten descriptions **in full** — what each tool does, when to
  choose it over the other two, what it returns
- Notes that `get_data` and `lookup` would compete even once rewritten, so the
  boundary between them has to be explicit

Score badly when the response:
- Blames the MCP configuration, the transport or the client
- Says only "make the descriptions better" without writing them
- Rewrites the implementations, which are not the problem
