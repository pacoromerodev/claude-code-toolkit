---
type: llm
weight: 1
---

Two faults are planted in `.claude/skills`:

1. `changelog-entry/SKILL.md` declares `name: write-changelog`. The name does
   not match the directory, so the skill never resolves — this is the one that
   is not triggering, and it is an error, not a style point.
2. `migration-check` has a description that says what the skill is and never
   says when to use it, and opens with "This skill".

Score well when the response:
- Identifies the name/directory mismatch as the reason a skill does not fire
- Also flags the description with no trigger
- Explains the consequence of each — does not resolve at all vs fires by luck —
  rather than listing them flatly
- Gives the concrete fix: the exact name to use, or a rewritten description

Score badly when the response:
- Reports only one of the two faults
- Lists findings with no fix
- Suggests unrelated changes, like reformatting the body, as if they were the
  cause
