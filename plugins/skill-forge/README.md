# skill-forge

Write skills that actually fire, and find out why the ones that don't.

```
/plugin install skill-forge@pacoromerodev
```

## Why this exists

At startup, Claude Code loads only a skill's **name and description**. Whether
the skill ever runs is a semantic match against that one field. The body can be
perfect and never be read.

So when a skill does not fire, the description is almost always why — and
everything here is built around that fact.

## Components

| Component | Type | Fires when |
|---|---|---|
| `write-a-skill` | Skill | You ask to write, create or scaffold a skill, or an existing one is not triggering |
| `audit-skills` | Skill | You ask to check, review or audit skills, or a skill is not triggering. Also `/skill-forge:audit-skills` |
| `skill-describer` | Subagent | A description needs writing or rewriting, or two skills overlap |

## The auditor

```bash
python3 plugins/skill-forge/scripts/audit_skills.py .claude/skills
python3 plugins/skill-forge/scripts/audit_skills.py ~/.claude/skills --json
```

Exit 1 on any error; warnings alone exit 0.

**Errors** — the skill is broken, not merely improvable:

| Finding | Effect |
|---|---|
| `name` does not match its directory | Never resolves. The skill is simply absent |
| Directory with no `SKILL.md` | Silently never loads |
| No frontmatter, or never closed | Never loads |
| No `description` | Nothing can match it |
| `name` > 64 or `description` > 1024 characters | Rejected |
| Body over 500 lines | Too big to stay coherent |

**Warnings** — judgement calls:

- **description never says when to use the skill.** It reads as a definition.
  This is the single most common reason a working skill sits unused.
- **description overlaps N% with another.** Both match the same prompts, so
  which one fires is arbitrary. Pointed at a plugin's `skills/`, the auditor
  compares against the agents and commands beside it too: the model chooses
  between all three on their descriptions, so a command that restates its
  skill is the same collision.
- **`references/x.md` never mentioned.** A file that never loads.
- **script not executable.**

The auditor runs as a script, never read into context — which is how it can be
this thorough for the price of a one-line description.

## skill-describer

Returns three candidates that differ in **coverage**, not wording: narrow, broad
and balanced. For each, the prompts it fires on, the realistic prompt it misses,
and what it would wrongly catch. Then a recommendation, an overlap check against
existing skills, and an "Obstacles encountered" section.

## Tests

```bash
plugins/skill-forge/tests/run.sh
```

29 assertions: every planted fault in `fixtures/broken/` must be found, the
clean tree in `fixtures/clean/` must stay silent, exit codes must be right, the
`--json` output must parse, and **this repository's own skills must pass**.

The quiet half matters as much as the loud half. A linter with false positives
gets ignored, which is the same as not having one.

## Evals

```bash
claude plugin eval plugins/skill-forge --scaffold --allow-tools Bash
```

- **audit-finds-faults** — a skills folder with a name/directory mismatch and a
  triggerless description. Both must be found, with the consequence of each
  explained, not just listed.
- **description-rewrite** — a real skill body behind the description "Kafka
  consumer helper." The rewrite must put the trigger in user language.
- **not-fired** — a conceptual question about skills, which must not start an
  audit.

## Requirements

Python 3.8+ on `PATH`. Standard library only.
