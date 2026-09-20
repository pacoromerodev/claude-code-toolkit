---
type: llm
weight: 1
---

This is a question about the project's layout, not a request to verify a
change. The right response simply answers it: names the framework and points
at the test directory.

Score badly if the response runs the full verification procedure — executing
the suite, reading the diff, hunting for weakened tests — or produces a
verification report with a verdict. Firing the verification skill here would
be a false positive, and the cost lands on every unrelated question the user
asks.
