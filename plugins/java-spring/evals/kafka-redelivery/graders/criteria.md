---
type: llm
weight: 1
---

The double charging follows from three things in the fixture:

1. Kafka delivery is at-least-once, so the message arrives twice on any
   rebalance or redeploy. This is the root cause, not a detail.
2. `enable-auto-commit: true` acknowledges on a timer, independently of whether
   the handler finished — so a crash mid-handler replays the message.
3. The handler is not idempotent: `gateway.charge` and `ledger.increment` both
   apply again on redelivery.

Score well when the response:
- Names at-least-once delivery as the reason, rather than hunting for a bug in
  the handler's logic
- Identifies auto-commit as wrong here and says what to use instead — manual
  acknowledgement, after the work
- Says the handler must be idempotent, and gives a concrete mechanism: a
  processed-message key written in the same transaction, or an upsert
- Notes that there is no error handler or dead letter topic

Score badly when the response:
- Suggests a lock, a retry, or a database constraint as the whole fix without
  addressing redelivery
- Treats it as a producer bug with no evidence
- Rewrites the listener without explaining why it was being redelivered
