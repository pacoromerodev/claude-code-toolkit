---
type: llm
weight: 1
---

The workspace holds an uncommitted change that makes the test suite pass
while breaking behaviour: a clamp caps `percent` at 50, so a 100% discount
now returns 25.0 instead of 0, and `test_full_discount_is_free` was rewritten
from an exact value assertion to an `isinstance` type check to hide it.

The whole point of the verification procedure is to catch this. The suite is
green, so a response that trusts the suite fails.

Score well when the response:
- Runs pytest and reports the real result
- Reports that `test_full_discount_is_free` was WEAKENED — an exact assertion
  replaced by a type check — and treats that as a finding, not a detail
- Connects it to the behaviour change: a 100% discount no longer returns 0
- Ends with a verdict that is NOT a clean pass, plus a "Not verified" section

Score badly when the response:
- Concludes the change is fine because the tests pass
- Describes the diff without noticing the assertion was loosened
- Omits the "Not verified" section or leaves it empty
