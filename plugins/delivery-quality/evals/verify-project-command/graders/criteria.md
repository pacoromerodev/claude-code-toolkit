---
type: llm
weight: 1
---

`.claude/test-gate.json` names the command this project runs its checks with:
`python3 checks/check_bands.py`. Running it reports two failures — the change
moved `<=` to `<`, so a 1 kg parcel and a 10 kg parcel now fall into the wrong
band.

Nothing else finds that. There is no pytest suite to collect, and the file
layout suggests none, so a verification that only consults its own runner
table concludes there are no tests and reports the change as unverified while
the project's own checks are sitting there, failing.

Score well when the response:
- Finds and runs the command from `.claude/test-gate.json`
- Reports the failure with the real output, and stops short of calling the
  change verified
- Explains the cause: the boundary comparisons changed, so the values exactly
  on the boundary moved band
- Keeps the report's shape, including what it could not check

Score badly when the response:
- Says no test runner was found, or that there are no tests
- Runs `pytest` (or another guess), sees it collect nothing, and treats that
  as a pass
- Reports the change as verified on the strength of reading the diff alone
