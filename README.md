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

### delivery-quality

Five components, each solving a different failure of unsupervised work.

| Component | Type | What it does |
|---|---|---|
| `verify-changes` | Skill | Runs the project's tests, reads the full diff, and checks that no test was weakened, skipped or deleted to make the suite pass. Reports with evidence and a required "Not verified" section. |
| `code-reviewer` | Subagent | Reviews the uncommitted change read-only and returns findings ranked by severity, with an "Obstacles encountered" section so its blind spots stay visible. |
| `guard_secrets` | PreToolUse hook | Blocks any write that would put a real credential on disk — API keys, private keys, connection strings with passwords, writes to `.env` and friends. |
| `guard_destructive` | PreToolUse hook | Blocks the shell commands that cannot be undone: `rm -rf` outside the project, a force-push to a protected branch, `git reset --hard` with work not yet pushed, `DROP`/`TRUNCATE`/unfiltered `DELETE` against a database, a disk written directly. |
| `test_gate` | Stop hook | Opt-in. Runs the test suite before the session is allowed to end, and refuses to end it while tests fail. |

`/review-diff` launches the subagent. The skill answers to `/delivery-quality:verify-changes`, or fires on its own when a change needs verifying.

#### Enabling the test gate

The Stop hook stays inert until a project asks for it. Enable it per project:

```bash
mkdir -p .claude && touch .claude/test-gate     # runner auto-detected
```

Maven, Gradle, npm, pytest, Go and Cargo are detected from the files present. For anything else, write the command yourself:

```bash
cat > .claude/test-gate.sh <<'EOF'
#!/usr/bin/env bash
./scripts/ci-test.sh --fast
EOF
chmod +x .claude/test-gate.sh
```

The gate never blocks the session outright. When tests fail it hands the failures back as context for the turn to continue with; when the suite hangs it kills it — after the project's timeout, or 940 seconds, whichever is smaller, so the report arrives before Claude Code's own hook timeout cuts it off — and says to find the hanging test rather than raise the limit. If the hook itself crashes, the session ends.

#### What the secret guard blocks

AWS access keys, Anthropic and OpenAI keys, GitHub and Slack tokens, Stripe live keys, Google API keys, private key blocks, JDBC and other connection strings carrying a password, and writes to `.env`, `credentials`, `id_rsa`, `.npmrc` and similar.

Values that are obviously not real — anything containing `EXAMPLE`, `PLACEHOLDER`, `REDACTED`, `<angle brackets>` or `${VARS}` — pass through. If the guard itself fails, it exits clean: a broken hook must never block a session.

---

## Design rules

The components here follow a few rules that came out of building them, and each one exists because the opposite failed:

- **A report is not evidence.** Skills and subagents end with command output and a diff, never with "everything looks good".
- **Name what you did not check.** `verify-changes` requires a "Not verified" section; `code-reviewer` requires "Obstacles encountered". A subagent returns only its summary, so an unstated gap is an invisible one.
- **A subagent's output format is the design.** Deciding what it returns matters more than describing what it is. There are no "expert persona" agents here.
- **Minimum tools.** The reviewer has no edit tools and does not get them. If a fix is obvious it describes the fix and lets the main thread apply it.
- **Hooks fail open.** A guard that crashes lets the call through. Determinism is worth having only while it cannot brick the session.
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
│   ├── agents/*.md, commands/*.md
│   ├── hooks/hooks.json, scripts/*.py
│   ├── tests/                        # fixture tests for every hook and script
│   └── evals/<case>/                 # plugin eval cases and their measurements
├── .github/scripts/                  # the CI checks, each with its own fixtures
├── scripts/                          # local eval runner and routing check
└── docs/anatomy.md                   # which component type to reach for
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

- Claude Code 2.x
- Python 3.8+ on `PATH` for the hooks (no third-party packages)

## Where this came from

Five plugins are built. [ROADMAP.md](ROADMAP.md) records what each one contains, which course material it draws on, and the corrections the work turned up along the way. Two more, `java-spring` and `mcp-builder`, were retired on 2026-09-25, and `skill-forge` was cut down to its auditor and its routing log: across every eval case, what was removed scored exactly what the model scores with no plugin loaded ([ROADMAP-v2.md](ROADMAP-v2.md), *Measured in full* and the proposals after it).

## Origin

Built on the 22 courses of [Anthropic Academy](https://academy.claude.com/) — Claude Code, the Claude API, MCP, Enterprise deployment and AI Fluency — and on applying them to day-to-day backend work.

## License

MIT — see [LICENSE](LICENSE).
