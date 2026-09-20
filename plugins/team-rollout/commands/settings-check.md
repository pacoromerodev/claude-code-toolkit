---
description: Review settings files for permissions wider than intended, and hooks that will not fire
---

Review the settings using the `settings-review` skill.

$ARGUMENTS

Default to every settings file in the repository plus `~/.claude/settings.json`
if it exists. For each finding, say which of the four locations the rule
actually belongs in — a correct rule in the wrong file is a common cause of
"this is being ignored".
