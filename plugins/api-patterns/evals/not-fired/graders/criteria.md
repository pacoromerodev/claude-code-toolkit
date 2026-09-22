---
type: llm
weight: 1
---

A factual question with a short answer: roughly 500–750 tokens for a page of
English prose, since a token averages about four characters.

Score well when the response:
- Gives a figure in that range, or close to it, with the rule of thumb behind it
- Stays short

Score badly if the response audits a codebase, discusses caching strategy,
builds an eval, or produces a cost analysis. Running an audit in answer to a
unit-conversion question is a false positive.
