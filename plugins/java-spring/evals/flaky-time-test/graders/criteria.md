---
type: llm
weight: 1
---

The test depends on the machine's clock and on how fast CI is, so raising
the sleep buys a slower suite and the same flakiness later. Time is a
dependency: inject a clock, and the ten-minute rule becomes a test that
asserts the rule rather than the machine.

Score well when the response:
- Says raising the sleep does not fix it, and why: the dependency is on real
  time, so the failure comes back
- Recommends injecting a clock (a `Clock` field, a time supplier) and
  advancing it in the test
- Shows the rewritten test asserting the actual rule — expired after ten
  minutes, not expired before — with no sleep
- Points out that the second assertion tests almost nothing as written

Score badly when the response:
- Recommends a longer sleep, a retry, or marking the test flaky
- Recommends mocking `Instant.now` through a static mock as the first choice
- Rewrites the test without removing its dependence on real time
