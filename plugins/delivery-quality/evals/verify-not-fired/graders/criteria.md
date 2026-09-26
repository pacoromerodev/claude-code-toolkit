---
type: llm
weight: 1
---

This is a question about the project's layout, not a request to verify a
change. The project uses pytest (configured in `pyproject.toml`, with
`testpaths = ["tests"]`), and its tests live under `tests/`, currently
`tests/unit/test_cart.py`.

Score well when the response:
- Names pytest and says its configuration is in `pyproject.toml`
- Points at the `tests/` directory

Do not mark a response down for length or for practical notes about the setup
— that pytest is not declared as a dependency, that the `src/` layout needs
the package installed or `pythonpath` set. Those answer the question asked.
What this case is for is the verification skill firing when it should not,
and the three signs of that are below.

Score badly if the response:
- Runs the full verification procedure — executing the suite, reading the
  diff, hunting for weakened tests
- Produces a verification report with a verdict
- Describes, reviews or passes judgment on the uncommitted change in
  `src/shop/cart.py`. One line noting that uncommitted changes exist is not a
  review and is not a reason to fail.

Firing the verification skill here would be a false positive, and the cost
lands on every unrelated question the user asks.
