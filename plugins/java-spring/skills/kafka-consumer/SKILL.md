---
name: kafka-consumer
description: Rules for writing or reviewing a Kafka consumer, listener or producer — acknowledgement, idempotency, retries, dead letter topics and consumer group configuration. Use when adding or changing a @KafkaListener, when messages are being reprocessed or lost, when a partition is stuck, or when setting up retry and DLT handling.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Kafka consumers

Start from the fact that decides everything else: **delivery is at-least-once.**
A message will be delivered twice. Not rarely — routinely, on every rebalance,
every redeploy, every time a commit does not land before a crash.

Every rule below follows from that.

## Idempotency is not optional

A handler that is not idempotent is a handler that corrupts data on redelivery.

Ways to get there, cheapest first:

1. **Natural idempotency** — the operation is a set, not an increment.
   `status = SHIPPED` is safe; `count = count + 1` is not.
2. **Upsert on a business key** rather than insert.
3. **A processed-messages table** keyed by message id, written in the same
   transaction as the effect. Prune it on a schedule.

Never rely on "it probably will not happen twice".

## Acknowledgement

Manual. `enable.auto.commit=false`.

```yaml
spring:
  kafka:
    consumer:
      enable-auto-commit: false
    listener:
      ack-mode: manual_immediate
```

Auto-commit acknowledges records on a timer, which means records the handler
has not finished — and, if the process dies in between, records that are
silently never processed. That is the one failure mode nobody notices, because
nothing errors.

Acknowledge **after** the work, never before, never in a `finally`.

## Retries and the dead letter topic

A poison message must not block its partition. Kafka has no per-message
redelivery — a stuck message stops everything behind it in that partition.

```java
@Bean
public DefaultErrorHandler errorHandler(KafkaTemplate<Object, Object> template) {
    var recoverer = new DeadLetterPublishingRecoverer(template);
    var backOff = new ExponentialBackOffWithMaxRetries(3);
    backOff.setInitialInterval(500);
    backOff.setMultiplier(2.0);
    var handler = new DefaultErrorHandler(recoverer, backOff);
    handler.addNotRetryableExceptions(ValidationException.class);
    return handler;
}
```

Distinguish the two kinds of failure:

- **Transient** — the downstream is down. Retry with backoff.
- **Permanent** — the payload is malformed, a field is missing. Retrying it a
  thousand times changes nothing. Straight to the DLT.

`addNotRetryableExceptions` is how you say which is which. Without it, a
validation error burns the whole retry budget.

**A DLT nobody watches is a silent data loss queue.** Alert on its depth. Have
a documented way to replay from it.

## Consumer groups and offsets

`auto.offset.reset` decides what a *new* consumer group does when it has no
committed offset:

| Value | On a new group | When it bites |
|---|---|---|
| `latest` | Starts at the end, skipping history | A renamed group silently skips every message published before the deploy |
| `earliest` | Replays the whole topic | A renamed group reprocesses months of history at once |

Neither is safe by default — the danger is **renaming the group**, which most
people do without realising it creates a new one. Treat the group id as part of
the contract.

## Ordering

Ordering is per partition, guaranteed only by key. If order matters for an
entity, its id must be the message key. Concurrency above one consumer per
partition does nothing.

## Producing

- `acks=all` when the message matters
- `enable.idempotence=true` to stop duplicates from producer retries
- A schema, and a plan for evolving it: adding a required field breaks every
  consumer still on the old version

## Testing

Testcontainers with a real broker. An embedded or mocked broker will not
reproduce a rebalance, and rebalances are where consumers actually break.

Test at minimum: the same message twice produces one effect; a permanent
failure reaches the DLT and does not retry; a transient failure retries and
then succeeds.

## What to check before calling it done

- Handler is idempotent, and you can say *why* in one sentence
- Manual ack, after the work
- Error handler with a DLT, and non-retryable exceptions named
- Key set deliberately when ordering matters
- Group id unchanged, or the consequence of changing it understood
- A test that delivers the same message twice
