# claude-code-toolkit

Installable Claude Code plugins: skills, subagents, hooks and commands for real software delivery workflows.

This is a **plugin marketplace**. Add it once and install any plugin from it.

```
/plugin marketplace add pacoromerodev/claude-code-toolkit
/plugin install delivery-quality@pacoromerodev
```

---

## Plugins

| Plugin | What it gives you |
|---|---|
| **[delivery-quality](plugins/delivery-quality)** | Verification before you trust a change: a skill that runs the tests and reads the diff, a read-only review subagent, guards against writing secrets and running destructive commands, and an opt-in test gate. |
| **[skill-forge](plugins/skill-forge)** | Find out why skills do not fire: a mechanical auditor for the faults that stop a skill or subagent loading or matching, and an opt-in log of which components fire in real use. |
| **[context-discipline](plugins/context-discipline)** | Keep the working state that compaction blurs: a tree snapshot taken before compaction and handed back after it, a skill for scoping work before writing it, and an auditor for the CLAUDE.md rules that get ignored. |
| **[api-patterns](plugins/api-patterns)** | *Experimental.* Patterns for building on the Claude API that carry their own verification: an eval pipeline with graders that discriminate, a caching auditor for breakpoints that silently miss, hybrid retrieval fused with RRF, and a reviewer for tool schemas. |
| **[team-rollout](plugins/team-rollout)** | Deploy Claude across a team without the expensive mistakes: the five rollout decisions in the order that keeps them from being redone, reference settings, and a checker for permissions wider than intended. |

### Quick start

Install one plugin, then try the thing it is for. Each link goes to the
plugin's README, which has every component and every setting.

| Plugin | After installing, try |
|---|---|
| [delivery-quality](plugins/delivery-quality) | Make a change, then ask Claude to verify it: the `verify-changes` skill runs the tests, reads the diff and says what it could not check. `/review-diff` gets a read-only review. The guards need nothing; the test gate is opt-in: `mkdir -p .claude && touch .claude/test-gate` |
| [context-discipline](plugins/context-discipline) | Nothing to do for the compaction snapshot. Ask for a review of your `CLAUDE.md`, or give a large, vague task and watch it get scoped before any code. `/handoff` writes a note for the next session |
| [skill-forge](plugins/skill-forge) | `python3 "$(ls -d ~/.claude/plugins/cache/pacoromerodev/skill-forge/*/ | sort -V | tail -1)scripts/audit_skills.py" .claude/skills` on your own skills (the path is where Claude Code installs it; the `ls` picks the newest installed version). The routing log is opt-in: `mkdir -p .claude && touch .claude/routing-log` |
| [team-rollout](plugins/team-rollout) | Ask how to roll Claude out to a team, or have a `settings.json` or managed policy reviewed before it ships |
| [api-patterns](plugins/api-patterns) | *Experimental.* Ask why prompt caching is not cutting your bill, how to know whether a prompt change helped, or how to fix retrieval that misses obvious matches |

### Status

What each plugin costs in every session, and what it measured against the
same prompts with no plugin loaded (2026-09-26, `claude-opus-5-5`, graded by
`claude-sonnet-5`, three runs a side).

| Plugin | Version | Always-on context | Cases | Mean Δ against no plugin |
|---|---|---|---|---|
| delivery-quality | 0.4.0 | ~360 tokens | 8 | +0.38 |
| team-rollout | 0.2.0 | ~230 tokens | 5 | +0.47 |
| context-discipline | 0.3.0 | ~320 tokens | 6 | +0.28 |
| skill-forge | 0.2.1 | ~0 tokens | 1 | +0.00 (it is a linter and a log; nothing to beat) |
| api-patterns | 0.2.0 | ~630 tokens | 10 | **−0.10** |

Context cost is `claude plugin details <plugin>@pacoromerodev`. The numbers
behind the Δ column are in each plugin's `evals/measurements.json`, and
`python3 .github/scripts/check_eval_freshness.py` says which are no longer
current because a case or the component it exercises changed.

---

## Design rules

The components here follow a few rules that came out of building them, and each one exists because the opposite failed:

- **A report is not evidence.** Skills and subagents end with command output and a diff, never with "everything looks good".
- **Name what you did not check.** `verify-changes` requires a "Not verified" section; `code-reviewer` requires "Obstacles encountered". A subagent returns only its summary, so an unstated gap is an invisible one.
- **A subagent's output format is the design.** Deciding what it returns matters more than describing what it is. There are no "expert persona" agents here.
- **Minimum tools.** The reviewer has no edit tools and does not get them. If a fix is obvious it describes the fix and lets the main thread apply it.
- **Hooks fail open.** A guard that crashes lets the call through. Determinism is worth having only while it cannot brick the session.
- **What a component reads is data, never instructions.** A diff, a file or a commit message that tells the reviewer to approve something is a finding. The instructions come from the user and from the plugin, nowhere else.
- **Exit 2 is the only blocking code.** It returns stderr to Claude as feedback, so the model sees the reason and can correct itself. Everything else is non-blocking.

---

## Layout

```
.
├── .claude-plugin/marketplace.json   # the catalogue this repo exposes
├── plugins/<name>/
│   ├── .claude-plugin/plugin.json
│   ├── README.md, CHANGELOG.md
│   ├── skills/<skill>/SKILL.md       # plus references/ where a skill needs them
│   ├── agents/*.md
│   ├── hooks/hooks.json, scripts/*.py
│   ├── tests/                        # fixture tests for every hook and script
│   └── evals/<case>/                 # plugin eval cases and their measurements
├── .github/scripts/                  # the CI checks, each with its own fixtures
├── scripts/                          # local eval runner and routing check
└── docs/
    ├── anatomy.md                    # which component type to reach for
    └── history/                      # the audits and plans, in order
```

`${CLAUDE_PLUGIN_ROOT}` resolves to the installed plugin's directory — always
use it in hook commands, never a relative path. [CONTRIBUTING.md](CONTRIBUTING.md)
has the full layout of a plugin and the steps for adding one.

---

## Development

The commands a change must pass before it is committed are in
[CLAUDE.md](CLAUDE.md), and CI runs the same set on every pull request. Eval
suites are separate: they cost money or plan usage and need a logged-in CLI,
so there is no eval workflow. Run them by hand with `scripts/run-evals.sh`
before a release. See [CONTRIBUTING.md](CONTRIBUTING.md) for the rules a
change is reviewed against, and [docs/anatomy.md](docs/anatomy.md) for which
component type to reach for.

## Requirements

- Claude Code 2.x; CI validates with 2.1.282
- Python 3.8+ on `PATH` for the hooks (no third-party packages)

## Where this came from

Five plugins are built. [ROADMAP.md](docs/history/ROADMAP.md) records what each one contains, which course material it draws on, and the corrections the work turned up along the way. Two more, `java-spring` and `mcp-builder`, were retired on 2026-09-25, and `skill-forge` was cut down to its auditor and its routing log: across every eval case, what was removed scored exactly what the model scores with no plugin loaded ([ROADMAP-v2.md](docs/history/ROADMAP-v2.md), *Measured in full* and the proposals after it). Every audit and plan behind the plugins is in [docs/history/](docs/history/README.md).

## Origin

Built on the 22 courses of [Anthropic Academy](https://academy.claude.com/) — Claude Code, the Claude API, MCP, Enterprise deployment and AI Fluency — and on applying them to day-to-day backend work.

## Security

The hooks run with your privileges. [SECURITY.md](SECURITY.md) says what they
touch, what they are not, and how to report a way past one.

## License

MIT — see [LICENSE](LICENSE).
