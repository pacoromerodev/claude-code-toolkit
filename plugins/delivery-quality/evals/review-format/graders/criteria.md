---
type: llm
weight: 1
---

The review must come back in the structure the code-reviewer subagent defines,
and that structure must survive being relayed to the user.

Score well when the response:
- Groups findings as Blocking / Worth fixing / Noted, keeping every heading
  even when a section is empty
- Anchors each finding to a file and line
- States, for each finding, the concrete input or state that makes it fail —
  not a style preference
- Includes an "Obstacles encountered" section naming what the review could not
  check
- Ends with a verdict on whether the change is safe to merge

Score badly when the response:
- Returns loose prose with no severity grouping
- Drops the "Obstacles encountered" section, or replaces it with a claim that
  nothing limited the review
- Reports formatting or naming preferences as findings
- Edits any file: this review is read-only
