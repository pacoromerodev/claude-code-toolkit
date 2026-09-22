---
type: llm
weight: 1
---

Ordering in Kafka is per partition, and a random key scatters one order's
events across partitions, where nothing relates them. Eight threads then
process them concurrently. Sequence numbers and reordering logic are a large
amount of machinery to rebuild a guarantee the broker gives for free when the
key is right.

Score well when the response:
- Names the random key as the cause: ordering holds within a partition, and
  those events are not in one
- Says the order id should be the message key, so every event for one order
  lands in the same partition and is processed in sequence
- Addresses the load-spreading worry: partitions still spread across the
  topic, and keys distribute unless one entity is genuinely hot
- Points out that concurrency above one consumer per partition buys nothing
  for that partition
- Treats sequence numbers as a fallback for a case the key cannot cover, not
  as the first move

Score badly when the response:
- Designs the sequence-number and reordering solution as asked
- Recommends fewer threads or a single consumer as the fix, with no mention
  of keys
- Says Kafka guarantees global ordering, or that it does not guarantee any
