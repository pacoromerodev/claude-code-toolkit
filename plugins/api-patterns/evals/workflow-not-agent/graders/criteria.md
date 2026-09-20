---
type: llm
weight: 1
---

Every step is known in advance: classify into one of six categories, select a
template, fill two fields, send. That is a workflow — specifically routing
followed by chaining — and building it as an agent loop buys unpredictability,
cost and untestability for nothing.

Score well when the response:
- Says this does not need an agent, and says why: the steps are known
- Names the pattern — routing on the category, then a fixed chain
- Points out that each step is separately testable and can use a cheaper model
- Does not simply comply with the framing of "how should I structure the agent
  loop"

Score badly when the response:
- Designs an agent loop as asked, with no push-back
- Says "it depends" without reaching a recommendation
- Treats the choice as a matter of taste rather than of whether the steps are
  known
