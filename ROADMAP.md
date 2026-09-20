# Roadmap

How this repository gets from one plugin to a complete toolkit, and where each piece comes from.

The source material is the [`anthropic-academy-es`](https://github.com/pacoromerodev/anthropic-academy-es) repository: 22 Anthropic Academy courses, 468 lessons, with Spanish study notes in `web/src/*.md`. This roadmap turns what those courses teach into things that actually run.

**The rule that governs every item below:** a course concept earns a place here only when it becomes a component that does work — a skill, a subagent, a hook, a command, a settings template. Prose that only explains a concept belongs in the academy repo, not in this one.

---

## Source map

Which course note feeds which plugin. Paths are relative to the academy repo.

| Plugin | Primary sources |
|---|---|
| `delivery-quality` | `web/src/claude-code-in-action.md` (verification, permission modes, Stop hooks) · `web/src/introduction-to-subagents.md` (output format, minimum tools) |
| `context-discipline` | `web/src/claude-code-101.md` (context as working memory, CLAUDE.md) · `web/src/claude-code-in-action.md` (compaction, rewind, `/goal`, SessionStart) |
| `skill-forge` | `web/src/introduction-to-agent-skills.md` (SKILL.md contract, progressive disclosure, precedence) |
| `java-spring` | Own domain experience, reviewed against `web/src/claude-code-in-action.md` (rules that are specific and checkable) |
| `mcp-builder` | `web/src/introduction-to-model-context-protocol.md` (primitives, FastMCP) · `web/src/model-context-protocol-advanced-topics.md` (transports, sampling, roots) |
| `api-patterns` | `web/src/claude-with-the-anthropic-api.md` (evals, caching, RAG, tool use) · `web/src/claude-platform-101.md` (agentic loop, model choice) · `web/src/claude-in-amazon-bedrock.md` (Bedrock deltas, contextual retrieval) |
| `team-rollout` | `web/src/deploying-claude-enterprise-with-confidence.md` (five decisions, governance, spend, visibility) |

---

## Phase 0 — Foundations ✅ done

Do this before writing the second plugin. Every later phase depends on it, and retrofitting it across six plugins costs far more than doing it once.

### 0.1 CI that validates every manifest

`.github/workflows/validate.yml`, on push and pull request:

- Install Claude Code, run `claude plugin validate .` and `claude plugin validate plugins/<name>` for every plugin found
- Assert that each `plugins/*/` directory has a matching entry in `marketplace.json`, and that versions agree
- Lint the hook scripts: `python3 -m compileall`, and `ruff check` if adopted
- Run each hook script against its fixture payloads (see 0.2)

**Done when:** a pull request that breaks a manifest or a hook fails CI, verified by pushing a deliberately broken branch once.

### 0.2 Fixture tests for hooks

`plugins/<name>/tests/fixtures/*.json` — one payload per case — plus `tests/run.sh` asserting the expected exit code and a substring of stderr.

`delivery-quality` starts with the seven cases already exercised by hand: real Anthropic key, real AWS key, `AKIA…EXAMPLE` passthrough, `System.getenv` passthrough, write to `.env`, JDBC url with password, malformed JSON payload.

**Done when:** `tests/run.sh` passes locally and in CI, and adding a new secret pattern without a fixture fails review.

### 0.3 Eval suites

`claude plugin eval` runs `evals/**/case.yaml` (or `prompt.md` + `graders/*.md`) against a plugin. This is the only honest way to know a skill fires when it should.

Per plugin, at minimum:

- Two prompts that **should** trigger the skill, phrased differently from the description
- One prompt in the same domain that should **not** trigger it
- A grader checking the output shape, not the wording

**Done when:** `claude plugin eval plugins/<name>` runs green, and the baseline arm (no plugin) visibly differs from the plugin arm.

### 0.4 Versioning and release

- Semver per plugin; `plugin.json` and the `marketplace.json` entry must agree
- Release with `claude plugin tag plugins/<name>`, which validates that agreement and creates `<name>--v<version>`
- `CHANGELOG.md` per plugin, one section per version

**Done when:** `delivery-quality` is tagged `delivery-quality--v0.1.0` and the tag is pushed.

### 0.5 Repository docs

- `CONTRIBUTING.md`: the design rules from the README stated as review criteria
- `docs/anatomy.md`: what each component type is for and when to reach for which — the decision rules from the courses, written once so plugin READMEs can link rather than repeat

**Effort:** 6–8 h total for phase 0.

---

## Phase 1 — Finish `delivery-quality` ✅ done in v0.2.0

The plugin works; it is not complete.

### 1.1 Close the gaps in the guard

- Patterns still missing: Azure connection strings, GCP service-account JSON (`"private_key_id"`), JWT with a real payload, `.pem` file writes, Basic auth headers
- Decide and document the `Bash` matcher behaviour: today it inspects `command`; it should also catch `cat > file <<EOF` heredocs that write a secret
- Add a per-project allowlist: `.claude/secret-guard-allow` with one regex per line, for fixture files that legitimately contain key-shaped strings

### 1.2 Make the test gate usable on slow suites

- Support `.claude/test-gate.json` with `{"command": [...], "timeout": 600, "only_when_changed": ["src/**"]}` so a docs-only session is not gated
- Report the *first* failure prominently rather than the last 60 lines, which on Maven is usually the build summary and not the assertion

### 1.3 A `PreToolUse` guard for destructive commands

Separate script, same plugin: block `rm -rf` outside the project, `git push --force` to a protected branch, `git reset --hard` with uncommitted work, `DROP TABLE` in a non-test connection string. Same fail-open rule.

### 1.4 Documentation and evals

Plugin `README.md` with each component, its trigger and its failure mode. Eval suite per 0.3.

**Done when:** `claude plugin eval plugins/delivery-quality` is green, CI passes, version 0.2.0 tagged.

**Effort:** 5–7 h.

---

## Phase 2 — `context-discipline` ✅ done in v0.1.0

The courses are blunt that context is the scarce resource and that compaction loses detail. This plugin makes that survivable.

| Component | Type | Behaviour |
|---|---|---|
| `save-state` | PreCompact hook | Writes `.claude/state.md` — current goal, files touched, decisions taken, what is left — before compaction discards it |
| `restore-state` | PostCompact + SessionStart hook | Hands the snapshot back through `hookSpecificOutput.additionalContext`. **Correction:** this phase had assumed `PostCompact` did not carry the summary and that a `compact` matcher on `SessionStart` was needed. Claude Code 2.1's embedded hook documentation says `PostCompact` exists and receives the summary, so it is the primary event; `SessionStart` covers the different case of a fresh or resumed session |
| `scope-task` | Skill | Enforces Explore → Plan → Code → Commit on anything non-trivial: read before writing, state the plan, get agreement, then implement |
| `claude-md-doctor` | Skill | Audits a `CLAUDE.md` against what the courses say makes rules stick: specific and checkable, naming the alternative rather than only the prohibition, emphasis spent as a budget, imports expanded inline (`@file` does **not** save context) |
| `/handoff` | Command | Writes a handoff note for the next session, or for another person |

**Watch out:** two hooks writing one state file will fight a concurrent session. Namespace by session id, and gitignore the directory. *(Done: `.claude/state/<session_id>.md`.)*

**Done when:** a session compacted mid-task resumes with the goal intact, demonstrated on a real task; `claude-md-doctor` finds at least three real problems in an existing project `CLAUDE.md`.

**Effort:** 6–8 h.

---

## Phase 3 — `skill-forge` ✅ done in v0.1.0

Meta-tooling: the plugin that makes the rest cheaper to build. Sources are the agent-skills course, whose central claim is that when a skill does not fire, the description is almost always why.

| Component | Type | Behaviour |
|---|---|---|
| `write-a-skill` | Skill | Scaffolds `SKILL.md` correctly: `name` ≤64 and matching the directory, `description` ≤1024 answering *what it does* **and** *when to use it*, body under 500 lines, heavy material pushed to `references/` and `scripts/` |
| `audit-skills` | Skill | Scans a skills directory for the known failure modes: overlapping descriptions that make matching ambiguous, `SKILL.md` outside a directory of the same name, scripts without `+x`, bodies over 500 lines, tools declared but unused |
| `skill-describer` | Subagent | Given a skill body, writes three candidate descriptions and names the prompts each one would and would not match |
| `/new-skill` | Command | Runs the scaffold end to end |

**Done when:** `audit-skills` run against this repository's own plugins reports clean, and against a deliberately broken fixture reports every planted fault.

**Effort:** 5–6 h.

---

## Phase 4 — `java-spring` ✅ done in v0.1.0

The differentiator. Nothing in the courses covers this; it is domain knowledge, and the courses only supply the shape — rules that are specific and checkable, and a review agent with a fixed output format.

| Component | Type | Behaviour |
|---|---|---|
| `spring-boot-service` | Skill | House conventions for a new service: layering, configuration properties over `@Value`, constructor injection, no field injection, `@Transactional` boundaries and where they leak |
| `kafka-consumer` | Skill | Idempotency, manual ack, retry and DLT topology, consumer group naming, what to do about poison messages, why `auto.offset.reset` matters in a redeploy |
| `migration-review` | Subagent | Reviews Flyway/Liquibase changesets for the things that break a running deployment: non-concurrent index creation, `NOT NULL` without default on a populated table, a rename with consumers still reading the old column, irreversible steps with no down path |
| `java-21-modernize` | Skill | Records, sealed types, pattern matching, virtual threads — with the cases where virtual threads are the wrong answer (pinned carrier threads on `synchronized`, pooled JDBC) |
| `test-shape` | Skill | What to test at each level, why a mock-heavy unit test asserts the implementation, Testcontainers over mocked infrastructure |

**Warning — this is the plugin that can leak.** Employer specifics must not enter it: internal hostnames, registry URLs, repository names, branch conventions tied to a client, ticket-tracker project keys, anything lifted from a private codebase. Write every rule so it would be true at any company. Phase 7 audits this again before anything goes public.

**Done when:** each skill fires on a realistic prompt in a scratch Spring project, `migration-review` catches four planted faults in a fixture changeset, and a read-through confirms nothing employer-specific.

**Effort:** 10–14 h. The largest phase, and the most valuable.

---

## Phase 5 — `mcp-builder` ✅ done in v0.1.0

| Component | Type | Behaviour |
|---|---|---|
| `mcp-server-scaffold` | Skill | FastMCP server with the three primitives used correctly: tools for the model, resources for the application, prompts for the user — the distinction the intro course builds everything on |
| `choose-transport` | Skill | stdio vs StreamableHTTP vs `stateless_http=True`, stated as a decision with consequences: stateless scales behind a load balancer but loses session ids, server→client requests, sampling, progress and subscriptions |
| `mcp-roots-check` | Skill | Implements path restriction properly, because the SDK does not enforce roots — `list_roots()` tells you the boundary, `is_path_allowed` is yours to write |
| `mcp-review` | Subagent | Reviews an MCP server for the real failure modes: tool descriptions too vague to match (the courses' stated number-one cause of tool-use failure), unbounded results, missing progress on long calls, secrets in resource URIs |
| `/mcp-new` | Command | Scaffold plus Inspector run (`mcp dev server.py`) |

**Done when:** the scaffold produces a server that the Inspector connects to and that exposes one working tool, resource and prompt.

**Effort:** 6–8 h.

---

## Phase 6 — `api-patterns` ✅ done in v0.1.0

The largest body of source material — three API courses — and therefore the phase most at risk of turning into prose. Keep only what executes.

| Component | Type | Behaviour |
|---|---|---|
| `eval-harness` | Skill + `scripts/` | Builds the dataset → model → grader → score pipeline. Code graders for anything verifiable (`json.loads`, `ast.parse`, regex: 10 or 0), a model grader asked for strengths, weaknesses and reasoning before the number — without that the score drifts to a flat 6 — and the average of both |
| `prompt-cache-audit` | Skill | Checks a request for the cache rules that are silently violated: order is tools → system → messages, at most 4 breakpoints, 1024-token minimum, one-hour TTL, and `cache_read_input_tokens` as the only proof it worked |
| `rag-retriever` | Skill + `scripts/` | Chunking choice, embeddings, BM25 for rare terms and identifiers, and multi-index fusion with RRF (`Σ 1/(k+rank)`, k≈60) |
| `agent-or-workflow` | Skill | Forces the decision the courses insist on: known steps → workflow, because it is more precise and testable; unknown steps → agent. Names the patterns — chaining, routing, parallelisation, evaluator-optimizer |
| `tool-schema-review` | Subagent | Reviews tool definitions against the stated top cause of failure: descriptions too vague. Demands three to four sentences, explicit parameter semantics and error behaviour |

Bedrock and Vertex deltas — `converse`, `toolChoice`, `toolResult.status`, inference profiles — belong in a `references/` file inside `eval-harness` and `tool-schema-review`, loaded on demand, not as separate skills.

**Done when:** `eval-harness` produces a scored run on a real prompt with both grader types, and `prompt-cache-audit` flags every violation in a fixture request.

**Effort:** 10–12 h.

---

## Phase 7 — `team-rollout` ✅ done in v0.1.0

Not a plugin of skills but a settings and governance pack, from the Enterprise course.

- `settings/managed-settings.json` — reference managed policy: permission mode, allowed tools, `strictKnownMarketplaces`
- `settings/project-settings.json` — sane project defaults with every field commented
- `docs/rollout.md` — the five decisions in order (Structure and Identity → Access → Governance → Spend → Visibility), each one narrowing the next, and the four that are hard to undo: domain claiming, topology, IdP-to-role mapping, retention
- `docs/plugin-trust.md` — plugins run code with your privileges and their hooks stack. What to read before installing one, and how to run a private marketplace

**Done when:** a new machine configured from `settings/` reaches a working, restricted setup with no manual edits.

**Effort:** 4–5 h.

---

## Cross-cutting

**Dependency rule.** Hooks stay on the Python standard library. A toolkit that needs `pip install` before a hook runs will be disabled by whoever hits that friction first.

**Every plugin ships with:** its own `README.md`, an eval suite, fixture tests for any script, a `CHANGELOG.md`, and a marketplace entry whose version matches `plugin.json`.

**Never in this repository:** employer names, internal hostnames or URLs, repository or Jira identifiers, real credentials in fixtures — use the documented `EXAMPLE` and `${PLACEHOLDER}` forms the guard already recognises — and any text copied from Anthropic Academy. The concepts are free to use; the wording is not.

---

## All seven phases are complete

Every plugin ships with a README, a CHANGELOG, an eval suite, fixture tests and
a marketplace entry whose version matches its manifest. What remains is the
go-public checklist at the end of this file, and whatever the evals say when
they are run against a credential.

## Order and dependencies

```
Phase 0  foundations ──┬─> Phase 1  delivery-quality (finish)
                       ├─> Phase 2  context-discipline
                       └─> Phase 3  skill-forge ──┬─> Phase 4  java-spring
                                                  ├─> Phase 5  mcp-builder
                                                  └─> Phase 6  api-patterns
                                                               │
                                                  Phase 7  team-rollout <┘
```

Phase 3 before 4–6 because every later plugin is written faster once the scaffolding and the description auditor exist.

If time is short, the shortest path to a toolkit worth showing is **0 → 1 → 3 → 4**. Those four leave a repository with two finished plugins, working CI, evals, and the one plugin nobody else could have written.

**Total effort:** roughly 50–70 h across all phases.

---

## Before making this repository public

1. `git log -p | grep -iE "<employer terms>"` across the full history — a rewritten file still lives in old commits
2. Re-read every hook script and settings template for internal paths
3. Confirm no Academy text was copied verbatim: concepts yes, wording no
4. `claude plugin validate` and the eval suites green on a clean clone
5. A `README.md` whose install instructions someone else can follow without asking
