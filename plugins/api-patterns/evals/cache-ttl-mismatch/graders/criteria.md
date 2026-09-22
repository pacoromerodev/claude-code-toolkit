---
type: llm
weight: 1
---

A five-minute lifetime, refreshed on each hit, does not survive hours of
silence. Each burst writes the cache and never reads it, and a write costs
more than an uncached call — so the bill going up is exactly what this pattern
produces.

Score well when the response:
- Explains that the entry expires five minutes after the last hit, so each
  burst starts cold
- Says a write costs more than an ordinary call, which is why the bill rose
  rather than stayed flat
- Reaches the real options: the one-hour lifetime at twice the base input
  price for the write, weighed against the traffic; or accepting cold bursts
- Suggests checking `cache_read_input_tokens` against
  `cache_creation_input_tokens` to confirm before changing anything

Score badly when the response:
- Suggests a bigger prompt to cross a minimum
- Says caching is not working and should be removed, with no arithmetic
- Recommends the one-hour lifetime without mentioning what it costs
