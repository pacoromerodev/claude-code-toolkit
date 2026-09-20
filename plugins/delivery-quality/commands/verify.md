---
description: Run the tests, read the diff and report whether the change is actually verified
---

Verify the current change using the `verify-changes` skill.

$ARGUMENTS

Run all three checks — tests, full diff, and whether any test was weakened — and
finish with the report format the skill defines, including the "Not verified"
section. Do not skip a check because an earlier one passed.
