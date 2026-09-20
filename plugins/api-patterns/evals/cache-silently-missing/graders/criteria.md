---
type: llm
weight: 1
---

`datetime.now().isoformat()` is interpolated into the cached system prompt, so
the prefix differs on every call. The cache is written every time and never
read.

Score well when the response:
- Identifies the timestamp inside the cached prefix as the cause
- Explains that a cached prefix must be identical across calls
- States that this is **worse** than no caching, because the write premium is
  paid on every request with no hit to offset it
- Moves the timestamp after the breakpoint, into the messages, rather than
  removing caching
- Tells the user to check `cache_read_input_tokens` to confirm the fix

Score badly when the response:
- Blames the model, the token counts or the pricing
- Suggests removing caching as the fix
- Says the prefix is too short without noticing the timestamp
- Does not say how to verify the fix worked
