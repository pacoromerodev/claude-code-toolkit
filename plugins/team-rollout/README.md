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
| `strictKnownMarketplaces: true` | It is an array of source objects. A boolean reads as locked down, is rejected as the wrong type, and restricts nothing |
| `knownMarketplaces` | Not a setting. Nothing reads that key |
| A git marketplace with no `ref` | Whatever the default branch holds today is what the team installs tomorrow, hooks included |
| `./scripts/hook.sh` | Resolves against wherever the session started. The hook silently never runs |
| No timeout on a `Stop` hook | A hook that hangs there leaves the session unable to finish |
| Unparseable JSON, or a rejected value | An interactive session shows a Settings Error dialog; a `-p` run skips the file with no dialog and carries on. `claude doctor` lists what was dropped |

## Where a rule belongs

Highest wins: managed settings, then `claude --settings`, then
`.claude/settings.local.json`, then `.claude/settings.json`, then
`~/.claude/settings.json`. Managed settings cannot be overridden below, which
makes them right for the few rules that must hold and wrong for preferences.

**A project file is a statement about the team.** Personal preferences belong
in the user file. A correct rule in the wrong file is a surprisingly common
cause of "this is being ignored".

## Tests

```bash
plugins/team-rollout/tests/run.sh
```

26 assertions, including that the templates this plugin ships **pass the
checker this plugin ships**. A plugin whose own examples fail its own checker
is not one anyone should copy from.

Passing the checker is not the same as being accepted by Claude Code, which
validates settings against its own schema and drops what does not match. CI
holds the templates to that schema too:

```bash
python3 .github/scripts/validate_settings_schema.py
```

Neither check can prove the policy takes effect on a real machine. That part
is manual, once, on a machine where the managed file is deployed: run
`claude plugin marketplace add <a repo not on the list>` and confirm it is
refused.

## Evals

```bash
claude plugin eval plugins/team-rollout --scaffold --allow-tools Bash
```

- **settings-too-wide** — a file about to reach a team, with a literal key, a
  blanket allow and a relative hook path. All three must be found, with the
  credential treated as the urgent one.
- **rollout-order** — a spend question asked first; the answer must surface
  what comes before it.
- **connector-with-write** — one team asking for a write-capable connector.
  The answer must reach the three gates, read before write, and whose
  signature it needs.
- **not-fired** — "how do I switch permission modes", which deserves one line.

## Requirements

Python 3.8+ on `PATH`. Standard library only.
