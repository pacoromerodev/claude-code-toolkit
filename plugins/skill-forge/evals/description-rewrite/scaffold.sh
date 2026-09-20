#!/usr/bin/env bash
set -euo pipefail
mkdir -p .claude/skills/kafka-consumer
cat > .claude/skills/kafka-consumer/SKILL.md <<'SKILL'
---
name: kafka-consumer
description: Kafka consumer helper.
---

# Kafka consumers

House rules for writing a consumer.

- Manual acknowledgement, never auto-commit: an auto-commit acks records the
  handler has not finished processing.
- Every handler is idempotent. Redelivery is normal, not exceptional.
- A poison message goes to the dead letter topic after the configured retries,
  never blocks the partition.
- `auto.offset.reset` decides what happens to a new consumer group on a
  redeploy. Choose it on purpose.
SKILL
