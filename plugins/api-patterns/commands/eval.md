---
description: Build or run an eval for a prompt, so a change is measured rather than eyeballed
---

Set up or run an eval using the `eval-harness` skill.

$ARGUMENTS

If no dataset exists, build one first — the ordinary cases in their real
proportions, the edge cases, and the cases the current prompt gets wrong. Use
both a code grader and a model grader, and make the model grader state
strengths and weaknesses before the number.

Always report against a baseline. A score with nothing to compare it to is not
a result.
