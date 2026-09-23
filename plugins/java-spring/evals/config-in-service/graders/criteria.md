---
type: llm
weight: 1
---

A value read and parsed at the point of use fails at the point of use: a
missing or malformed setting surfaces on a request, in production, as a
NumberFormatException rather than at startup. Typed configuration binds and
validates once, when the context starts.

Score well when the response:
- Names the real cost: the failure is deferred to the first request that
  needs the value, instead of to startup
- Recommends binding configuration to a typed class, validated, so a bad
  value stops the application from starting
- Mentions that defaults belong in configuration rather than in code, so what
  is in effect is visible per environment
- Mentions testability: a value from the environment is hard to vary in a
  test, an injected object is not

Score badly when the response:
- Says it is a matter of taste, or only cites convention
- Recommends @Value on fields as the improvement, with no mention of
  validation or of failing at startup
- Recommends a configuration server or external system for a timeout
