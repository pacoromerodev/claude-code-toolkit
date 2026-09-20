# team-rollout

Deploy Claude across a team without the expensive mistakes.

```
/plugin install team-rollout@pacoromerodev
```

## Components

| Component | Type | Fires when |
|---|---|---|
| `plan-rollout` | Skill | Planning a deployment; onboarding a group; deciding who gets what |
| `settings-review` | Skill | Writing or reviewing settings; a hook does not fire |
| `settings/*.json` | Templates | Copied and narrowed |
| `/rollout-plan`, `/settings-check` | Commands | Typed |

## Five decisions, and the order is the content

```
Structure and Identity → Access → Governance → Spend → Visibility
```

Each narrows the next. Taken out of sequence, the earlier ones get redone — the
usual symptom being spend limits set before the group structure exists.

**Four are hard to undo:** claiming the domain (irreversible), one organisation
or several, the mapping from identity groups to roles, and retention. Decide
those with the person who owns the consequence present.

## Two things rollouts learn late

**Group membership is additive.** Someone in two groups gets the union. A
narrow group never takes away what a broad one granted — so anything regulated
needs its **own** group, not a narrower version of a general one.

**At a spend limit, usage pauses.** Nothing queues, nothing degrades. And
before raising any limit, check the group's default model and effort setting: a
group running an expensive model on routine work looks like a capacity problem
and is a configuration one. That is the most common false alarm in a rollout.

## The settings checker

```bash
python3 plugins/team-rollout/scripts/check_settings.py .claude/settings.json
python3 plugins/team-rollout/scripts/check_settings.py managed.json --managed
```

| Finding | Why |
|---|---|
| `"Bash"` in allow | Grants every command. Added to stop a prompt one afternoon, never narrowed after, because nothing prompts again to remind you |
| `bypassPermissions` as default mode | Disables the permission system for every session using the file |
| A literal credential | Settings files get committed and shared — treat it as leaked and rotate |
| No `strictKnownMarketplaces` | A plugin runs code with the user's privileges and its hooks stack with everyone else's |
| `./scripts/hook.sh` | Resolves against wherever the session started. The hook silently never runs |
| No timeout on a `Stop` hook | A hook that hangs there leaves the session unable to finish |
| Unparseable JSON | Claude Code ignores the file **silently** — every rule in it stops applying with no message |

## The four locations

Managed policy → user → project → local. More specific wins, except that a
managed policy cannot be overridden — which makes it right for the few rules
that must hold and wrong for preferences.

**A project file is a statement about the team.** Personal preferences belong
in the user file. A correct rule in the wrong one of the four is a surprisingly
common cause of "this is being ignored".

## Tests

```bash
plugins/team-rollout/tests/run.sh
```

22 assertions, including that the templates this plugin ships **pass the
checker this plugin ships**. A plugin whose own examples fail its own checker
is not one anyone should copy from.

## Evals

```bash
claude plugin eval plugins/team-rollout --scaffold --allow-tools Bash
```

- **settings-too-wide** — a file about to reach a team, with a literal key, a
  blanket allow and a relative hook path. All three must be found, with the
  credential treated as the urgent one.
- **rollout-order** — a spend question asked first; the answer must surface
  what comes before it.
- **not-fired** — "how do I switch permission modes", which deserves one line.

## Requirements

Python 3.8+ on `PATH`. Standard library only.
