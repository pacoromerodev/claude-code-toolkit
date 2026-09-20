---
type: llm
weight: 1
---

"Clean up the payment module" is open-ended, and `InvoiceJob` depends on
`PaymentService.charge`, so a refactor done straight away breaks a caller
nobody mentioned.

Score well when the response:
- Explores first — reads the module and looks for what depends on it
- Finds, or sets out to find, the caller in the billing package
- States a plan: what changes, what stays, what "done" means, what is out of
  scope
- Stops for agreement before editing, or asks what "clean up" should mean here

Score badly when the response:
- Starts rewriting files immediately
- Produces a generic refactoring checklist with no reference to this code
- Claims to be done without naming a verifiable finishing condition
