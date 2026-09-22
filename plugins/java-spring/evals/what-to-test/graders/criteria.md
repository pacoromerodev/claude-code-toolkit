---
type: llm
weight: 1
---

The discount rule is the part worth testing, and it needs neither Spring
nor a database: a plain unit test on the rule, with the repository as a stub
or the rule extracted from it. A full @SpringBootTest boots the context for
every run and tests the wiring, which is a different question and a slower
one.

Score well when the response:
- Says a full context test is the wrong level for a rule, and why — slow, and
  it tests wiring rather than behaviour
- Recommends a unit test on the rule, with the repository stubbed, or the
  rule extracted so no stub is needed
- Names what a slice or integration test is still for: the query the
  repository runs, the transaction boundary, the mapping
- Says to assert the outcome rather than the calls made — a test that asserts
  interactions breaks on every refactor

Score badly when the response:
- Recommends @SpringBootTest for this
- Recommends mocking everything, including the class under test's own logic
- Answers only "it depends" without a recommendation
