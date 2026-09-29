# skill-forge

Find out why a skill does not fire, and which ones fire in real use.

```
/plugin install skill-forge@pacoromerodev
```

## Why this exists

At startup, Claude Code loads only a skill's **name and description**. Whether
the skill ever runs is a semantic match against that one field. The body can be
perfect and never be read.

So when a skill does not fire, the description is almost always why — and
everything here is built around that fact.

Until 2026-09-25 this plugin also shipped a skill for writing skills, a skill
wrapping the auditor, and a subagent that drafts descriptions. All three
scored exactly what the model scores with no plugin loaded, across every eval
case, so they were removed (see `docs/history/ROADMAP-v2.md` in the repository, *Proposed for removal:
skill-forge*). What remains is what an eval cannot measure and the model
cannot do on its own: a linter that runs as a script, and a log of real use.

## Components

| Component | Type | What it is |
|---|---|---|
| `scripts/audit_skills.py` | Script | The auditor. Runs from a shell or CI; this repository's own CI runs it |
| `log_routing` | Hooks | Opt-in, per project: records prompts and what fired |
| `scripts/routing_report.py` | Script | Reads that log back |

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

### Subagents

Point it at a plugin's `skills/` and it audits the `agents/` beside it too — a
subagent is judged on what comes back, because that is all that does:

| Finding | Why |
|---|---|
| A reviewing agent with `Write` or `Edit` | The finding gets fixed in a context nobody sees, and the report says it was fine |
| No section for gaps in the output format | Only the summary returns, so anything unchecked disappears unless a heading keeps it |
| "You are a senior X expert" | Adds nothing the task description does not |
| A description that never says when to delegate | The main thread picks between agents on those descriptions alone |
| A description that never says what to pass | It also shapes the prompt the main thread writes when delegating |

The auditor runs as a script, never read into context — which is how it can be
this thorough for the price of a one-line description.

## Which components actually fire

An eval answers whether a skill helps, and costs a session per case. It
answers a smaller question on the way — did the skill fire at all — and that
one is free, from ordinary use.

```bash
mkdir -p .claude && touch .claude/routing-log      # opt in, per project
python3 plugins/skill-forge/scripts/routing_report.py
```

Two hooks feed one log: the prompt, and whatever skill or subagent the model
reached for. The subagent tool is `Agent` in current Claude Code and was
`Task` before; the hook matches both. Until 2026-09-25 it matched only `Task`,
so no delegation was logged — a log that misses a kind of event without saying
so is the failure it exists to catch. The report says what fired and how often, and — the part worth
reading — **which prompts fired nothing**. A case measures a prompt somebody
wrote for it; this measures the prompt somebody typed.

It logs what you type, so it stays off until you enable it, the log lives
outside the repository under the plugin's data directory, and the prompt is
truncated to 200 characters. Nothing leaves the machine.

It cannot tell you whether firing helped. That needs both arms of an eval, and
no log can produce them.

## Tests

```bash
plugins/skill-forge/tests/run.sh
```

45 assertions: every planted fault in `fixtures/broken/` must be found, the
clean tree in `fixtures/clean/` must stay silent, exit codes must be right, the
`--json` output must parse, and **this repository's own skills must pass**.

The quiet half matters as much as the loud half. A linter with false positives
gets ignored, which is the same as not having one.

## Evals

```bash
claude plugin eval plugins/skill-forge
```

One case, **not-fired**: a conceptual question about skills, which nothing here
may act on. A linter and a passive log have no answer of their own for an eval
to compare against a baseline, so the case checks only that they stay out of
the way.

### Measured

Last full pass on 2026-09-26: `claude-opus-5-5`, graded by `claude-sonnet-5`,
three runs a side, each case against the same prompt with no plugin loaded.

| Cases | Mean score | Mean Δ against no plugin | Δ > 0 | Δ < 0 |
|---|---|---|---|---|
| 1 | 1.00 | +0.00 | 0 | 0 |

The per-case numbers are in [`evals/measurements.json`](evals/measurements.json).
A number is only current while neither its case nor the component it
exercises has changed; `python3 .github/scripts/check_eval_freshness.py`
lists the ones that have. Re-measure with `scripts/run-evals.sh --model <id>
--stale`.

## Requirements

Python 3.8+ on `PATH`. Standard library only.
