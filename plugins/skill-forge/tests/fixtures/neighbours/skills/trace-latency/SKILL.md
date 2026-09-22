---
name: trace-latency
description: Finds where request latency is spent by reading traces and timing each span. Use when a request is slow, when a p99 regresses, or when a service got slower after a deploy.
allowed-tools: Read, Glob, Grep
---

# Trace latency

Read the traces, total the spans, report the slowest path.
