---
type: llm
weight: 1
---

Sixty-three tools is a catalogue, not a toolset, and a spec summary is written
for a developer reading the endpoint, not for a model choosing between
neighbours. More detail on all 63 makes the listing longer and the choice no
easier.

Score well when the response:
- Says the count is the problem, and that generating one tool per endpoint is
  what produced it
- Proposes grouping around what a user asks for — a few task-shaped tools
  that call several endpoints — rather than mirroring the API
- Says a description has to name the boundary against its neighbours: when to
  use this one rather than the one beside it
- Asks which endpoints are actually used, and suggests starting from the
  handful that carry the real traffic
- May mention that some of them are resources or prompts rather than tools

Score badly when the response:
- Recommends rewriting all 63 descriptions and stops there
- Recommends tool_choice, routing rules, or a bigger model
- Suggests splitting them across several servers with no reduction
