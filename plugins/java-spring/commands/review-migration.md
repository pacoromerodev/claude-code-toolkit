---
description: Review a database migration for what breaks during a rolling deploy
---

Launch the `migration-review` subagent on the migration.

$ARGUMENTS

Default to the migration files in the uncommitted diff when no path is given.
Relay its report in full, including "Obstacles encountered" and the deploy
order — those are the parts that decide whether this ships tonight.
