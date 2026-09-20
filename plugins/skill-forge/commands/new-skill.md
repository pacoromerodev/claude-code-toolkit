---
description: Scaffold a new skill, with the description written and audited before you keep it
---

Create a new skill using the `write-a-skill` skill.

$ARGUMENTS

Work in this order, and do not skip to the body:

1. Ask what situation the skill fires in, unless the arguments already say.
2. Write the body first, as a procedure.
3. Hand the body to the `skill-describer` subagent and use its recommended
   description rather than writing one inline.
4. Run the auditor over the result and report what it says.
5. Write the three eval cases — two that should fire it, one in the same
   domain that should not.
