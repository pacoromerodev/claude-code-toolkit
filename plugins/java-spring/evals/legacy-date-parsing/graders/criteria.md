---
type: llm
weight: 1
---

`SimpleDateFormat` is not thread-safe, and a static instance shared across
request threads is the classic way to get corrupted output under load — the
nonsense dates are that, not a logging problem. `DateTimeFormatter` is
immutable and thread-safe, so the same shape of code becomes correct.

Score well when the response:
- Identifies the shared mutable formatter as the cause of the wrong dates,
  and says it is a concurrency fault rather than a style one
- Replaces it with `DateTimeFormatter` and the `java.time` types, keeping the
  static field, because that one is safe to share
- Says what changes at the boundaries — `LocalDate` or `Instant` in place of
  `Date` — rather than converting back and forth
- Does not "fix" it with synchronisation or a ThreadLocal as the
  recommendation, though it may mention them as what people reach for

Score badly when the response:
- Treats it purely as an outdated API to modernise, with no mention of thread
  safety
- Recommends synchronizing the formatter, or a ThreadLocal, as the fix
- Recommends creating a new SimpleDateFormat per call and stops there
