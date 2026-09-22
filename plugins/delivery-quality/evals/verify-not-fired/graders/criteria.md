---
type: llm
weight: 1
---

This is a question about the project's layout, not a request to verify a
change. The project uses pytest (configured in `pyproject.toml`, with
`testpaths = ["tests"]`), and its tests live under `tests/`, currently
`tests/unit/test_cart.py`.

Score well when the response:
- Names pytest and says where the configuration is
- Points at the `tests/` directory
- Stays short: an answer to the question asked

Score badly if the response:
- Runs the full verification procedure — executing the suite, reading the
  diff, hunting for weakened tests
- Produces a verification report with a verdict
- Comments on the uncommitted change in `src/shop/cart.py`, which nobody asked
  about

Firing the verification skill here would be a false positive, and the cost
lands on every unrelated question the user asks.
