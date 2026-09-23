---
type: llm
weight: 1
---

Two faults are planted in `.claude/skills`:

1. `.claude/skills/SKILL.md` (the changelog skill) sits loose in the skills
   root instead of in a directory of its own. A skill is loaded from
   `<skills>/<name>/SKILL.md`, so this one never loads: it is the one that is
   not triggering, and it is an error, not a style point.
2. `migration-check` loads, but its description says what the skill is and
   never says when to use it, and it opens with "This skill".

Score well when the response:
- Identifies the loose `SKILL.md` as the reason a skill does not fire, and
  says it never loads
- Also flags the description with no trigger
- Explains the consequence of each — never loads versus fires by luck —
  rather than listing them flatly
- Gives the concrete fix: move the file to `.claude/skills/changelog-entry/SKILL.md`,
  and a rewritten description for `migration-check`

Score badly when the response:
- Reports only one of the two faults
- Treats the loose file as a naming problem, or says the skill will load
- Lists findings with no fix
- Suggests unrelated changes, like reformatting the body, as if they were the
  cause
