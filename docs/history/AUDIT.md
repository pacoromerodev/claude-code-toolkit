# Audit — second iteration

What the seven plugins actually do today, measured before the second iteration
changes anything. The companion plan is [`ROADMAP-v2.md`](ROADMAP-v2.md); the
first iteration's plan is [`ROADMAP.md`](ROADMAP.md).

| | |
|---|---|
| Commit audited | `fc84f6d` (`main`), clean tree |
| Claude Code | 2.1.274, plugins installed at user scope from this directory |
| Sources | the 22 notes in `anthropic-academy-es/web/src/*.md` (cited as `<course>.md:<line>`), the public Claude Code and Claude API docs fetched on the audit date |
| Date | 2026-09-21 |

Paths under the auditor's home directory are written as `~`. Nothing in this
file quotes the course notes; they are cited by line and paraphrased.

---

## Summary

The toolkit passes every check it runs on itself — `claude plugin validate`,
158 fixture tests, the stdlib and consistency scripts, the skill auditor — and
several of its central claims are still false. The checks pass because they
test the shapes the authors wrote, not the behaviour users rely on.

| Severity | Count | Meaning |
|---|---|---|
| Critical | 2 | A safety property the plugin advertises is absent, silently, for everyone who installs it |
| High | 7 | A component does the opposite of what it claims, or a measurement the repo relies on is wrong |
| Medium | 16 | Content contradicted by the sources, a stated rule that nothing enforces, or a defect with a workaround |
| Low | 7 | Cosmetic, or documentation drift |

The five that matter most:

1. **C1 — Skills grant themselves unprompted shell access.** In Claude Code,
   `allowed-tools` pre-approves tools; it restricts nothing. 16 of 18 skills
   list bare `Bash`, and 12 also list `Write` and `Edit`. `write-a-skill`
   teaches the opposite.
2. **C2 — The guards miss the common form of what they block, and the model
   can switch the secret guard off.** `git push --force origin main` and
   `rm -Rf ~/x` pass. Writing `.*` to `.claude/secret-guard-allow` then lets a
   blocked key through, and the block message tells the model to write that file.
3. **H1 — `restore_state.py` injects stale or foreign text as "measured facts"
   whenever a session begins.** It did so in the session that produced this
   audit, reporting the wrong branch. A file committed to any repository's
   `.claude/state/` is injected the same way.
4. **H4 — The reference managed policy restricts no marketplace.** The template
   sets `strictKnownMarketplaces: true`, which the published schema rejects
   (the setting is an array), and a key, `knownMarketplaces`, that does not
   exist. The settings checker calls it clean.
5. **H6 — The eval suite cannot show that the plugins help.** Two cases have no
   fixture and can never pass. Three graders are wrong. Of the 10 positive
   cases that ran with the tools they need, the no-plugin baseline passed 8,
   and the plugin beat it in only 2.

---

## 1. Mechanical baseline

### 1.1 Manifests

```
$ claude plugin validate . && for d in plugins/*/; do claude plugin validate "$d"; done
✔ Validation passed          (×8: marketplace + 7 plugins, every exit 0)
```

### 1.2 Always-on cost

`claude plugin details <plugin>@pacoromerodev`:

| Plugin | Skills listed | Agents | Hooks | Always-on |
|---|---|---|---|---|
| delivery-quality | review, verify, verify-changes | code-reviewer | PreToolUse, Stop | ~277 tok |
| skill-forge | audit-skills, **audit-skills**, new-skill, write-a-skill | skill-describer | — | ~370 tok |
| context-discipline | claude-md-doctor, context, handoff, scope-task | — | PreCompact, PostCompact, SessionStart | ~278 tok |
| mcp-builder | choose-transport, mcp-new, mcp-review, mcp-roots-check, mcp-server-scaffold | mcp-review | — | ~484 tok |
| api-patterns | agent-or-workflow, cache-audit, eval, eval-harness, prompt-cache-audit, rag-retriever | tool-schema-review | — | ~598 tok |
| team-rollout | plan-rollout, rollout-plan, settings-check, settings-review | — | — | ~300 tok |
| java-spring | java-21-modernize, kafka-consumer, new-endpoint, review-migration, spring-boot-service, test-shape | migration-review | — | ~614 tok |
| **All seven** | 32 entries (18 skills + 14 commands) | 5 | 5 events | **~2,921 tok per session** |

The 14 commands cost 30–40 tokens each (~470 in total). Twelve of them are
short wrappers around a skill or agent that is already listed; `/context` and
`/handoff` stand alone. `skill-forge` lists
`audit-skills` twice (see H3).

### 1.3 Fixture tests

Each runner was run from a fresh directory under the scratchpad, not from the
repository root:

| Runner | Result | Exit |
|---|---|---|
| api-patterns | 15 passed, 0 failed | 0 |
| context-discipline | 20 passed, 0 failed | 0 |
| delivery-quality | 47 passed, 0 failed | 0 |
| java-spring | 18 passed, 0 failed | 0 |
| mcp-builder | 21 passed, 0 failed | 0 |
| skill-forge | 15 passed, 0 failed | 0 |
| team-rollout | 22 passed, 0 failed | 0 |
| **Total** | **158 passed, 0 failed** | |

Side effects:
- After the run, the only file left in any of the seven working directories
  was `context-discipline/.claude/state/session.md`. See H1.
- `api-patterns/tests/run.sh` also imports `fuse`, which writes
  `plugins/api-patterns/scripts/__pycache__/` inside the repository whatever
  the working directory. That directory predates this audit and is gitignored.
- A subagent's probe during the audit created
  `plugins/delivery-quality/scripts/__pycache__/`. The auditor removed it
  before the commit.

### 1.4 The rest of CI, reproduced locally

| Step | Result |
|---|---|
| `python3 .github/scripts/check_consistency.py` | `OK — 7 plugin(s) consistent with the marketplace`, exit 0 |
| `python3 .github/scripts/check_stdlib_only.py` | `OK — 12 hook script(s) use only the standard library`, exit 0 (only 5 of the 12 are hooks) |
| `python3 -m compileall -q plugins/*/scripts/` (with `PYTHONPYCACHEPREFIX` pointing outside the repo) | exit 0 on 3.12 |
| `shellcheck -S warning` | not installed locally — see *Not verified* |
| Python 3.8 leg | no 3.8 interpreter locally — see *Not verified* |
| `python3 plugins/skill-forge/scripts/audit_skills.py plugins/*/skills` (not in CI) | `Clean — 18 skill(s) audited, nothing to report.`, exit 0 |

GitHub history (`gh run list --limit 50`): 9 runs, all `validate`, all `push`
to `main`, 8 success and 1 failure (shellcheck SC2034 in
`context-discipline/tests/run.sh`).

The `evals` workflow ran for the first time during the audit: run
35595913494, `schedule`, 2026-09-21 11:47 UTC, **failure**. Its log reads
`ANTHROPIC_API_KEY is not set — add it as a repository secret`. The weekly
eval cannot pass until that secret exists.

No branch or pull-request run exists (relevant to ROADMAP 0.1, see M9).

### 1.5 Eval suites

**Conditions.** The command in CONTRIBUTING.md and the plan was
`claude plugin eval <p>@pacoromerodev --scaffold --allow-tools Bash
--trust-plugin --no-publish`. It failed for all 44 runs, before any model call
and at $0. `plugin eval` refuses a Bash-granting run when the Docker credential
store contains a symbolic link. On this WSL machine `~/.docker/contexts` and
`~/.docker/features.json` link into the Windows home. The auditor did not modify
`~/.docker` or redirect `DOCKER_CONFIG`, because that would weaken the check.

The suites were then run without `--allow-tools`. That also gates `Write` and
`Edit`, not only `Bash`. The plan's account hit its session limit partway
through, which voided java-spring, team-rollout and two api-patterns cases. Those
cases, plus the two that needed file edits, were re-run with
`--allow-tools Write Edit`. Every case ran once per arm (`runs: 1` in every
`case.yaml`), with a haiku judge voting three times. Total model cost was
**$6.98** ($4.79 first pass, $2.11 re-run, $0.08 probe).

The suite has **22 cases**, not 20: 20 `case.yaml` files plus two `prompt.md`
cases in delivery-quality.

| Plugin | Case | Kind | With plugin | Baseline | Validity |
|---|---|---|---|---|---|
| delivery-quality | guard-blocks-destructive | hook | 1 | 0 | **degraded** — no Bash, so the guard never ran; the pass is for prose |
| delivery-quality | review-format | agent | 0 | 0 | **broken** — no scaffold; the case directory is empty (H6) |
| delivery-quality | verify-fires | skill | 0 | 1 | **degraded** — pytest cannot run; the skill fired (`tool_used: Skill` passed) and correctly reported "not verified" |
| delivery-quality | verify-not-fired | negative | 0 | 0 | **broken** — no scaffold; there is no project to answer about (H6) |
| skill-forge | audit-finds-faults | skill | 1 | 0 | degraded — the auditor script needs Bash |
| skill-forge | description-rewrite | agent | 0 | 1 | valid (re-run). With the plugin, the model asked which skill was meant |
| skill-forge | not-fired | negative | 1 | 1 | valid |
| context-discipline | claude-md-rewrite | skill | 1 | 1 | valid — does not discriminate |
| context-discipline | scope-before-code | skill | 1 | 1 | valid — does not discriminate |
| context-discipline | not-fired | negative | 1 | 1 | valid (re-run with Edit) |
| mcp-builder | stateless-tradeoff | skill | 1 | 0 | valid |
| mcp-builder | tool-never-called | agent | 1 | 1 | valid — does not discriminate |
| mcp-builder | not-fired | negative | 1 | 1 | valid |
| api-patterns | cache-silently-missing | skill | 1 | 1 | valid (re-run) — does not discriminate |
| api-patterns | workflow-not-agent | skill | 1 | 1 | valid (re-run) — does not discriminate |
| api-patterns | not-fired | negative | 1 | 1 | valid |
| team-rollout | rollout-order | skill | 1 | 0 | valid (re-run) |
| team-rollout | settings-too-wide | skill | 0 | 0 | degraded (checker needs Bash); the grader contradicts the skill (H6) |
| team-rollout | not-fired | negative | 0 | 0 | **grader broken** — failed a correct Shift+Tab answer twice (H6) |
| java-spring | kafka-redelivery | skill | 1 | 1 | valid (re-run) — does not discriminate |
| java-spring | migration-unsafe | agent | 1 | 1 | valid (re-run) — does not discriminate |
| java-spring | not-fired | negative | 1 | 1 | valid |

Positive cases marked valid, meaning they ran with the tools they need: 10.
`settings-too-wide` is excluded as degraded. Of the 10:
- the plugin beat the baseline in 2 (`stateless-tradeoff`, `rollout-order`);
- it tied in 7, all of them passes;
- it lost in 1 (`description-rewrite`);
- so the baseline passed 8 of 10.

With one run per arm none of these is statistically meaningful. But ROADMAP 0.3
set "the baseline arm visibly differs from the plugin arm" as the done-criterion,
and it is not met.

### 1.6 What CI validates today

| Validated on every PR | Not validated anywhere |
|---|---|
| Manifests (`claude plugin validate`) | Skill content: `audit_skills.py` is never run on `plugins/*/skills` |
| Marketplace entry, version, README, CHANGELOG, eval dir exist (`check_consistency.py`) | Command/skill/agent name collisions, within or across plugins |
| Hook scripts import only allowed modules | `allowed-tools` scope |
| Scripts compile on 3.8 and 3.12 | Settings templates against the published schema |
| Fixture tests pass | Fixture tests leave no files behind |
| `shellcheck -S warning` | CONTRIBUTING's three-cases-per-skill rule |
| | Any eval: the workflow is manual/weekly, covers one plugin, and its only run failed for want of the API-key secret |
| | Academy wording copied into the repo |
| | `hooks.json` commands use `${CLAUDE_PLUGIN_ROOT}` and point at existing scripts |

---

## 2. Findings

Every finding lists how it was established. Items tagged *(reviewer, reproduced)*
came from the `code-reviewer` subagent (§3) and were re-run by the auditor
before inclusion.

### Critical

#### C1 — `allowed-tools` pre-approves broad tools; the toolkit uses it as a restriction

- **Evidence.** Claude Code docs, *Skills → Pre-approve tools for a skill*: the
  field "grants permission for the listed tools during the turn that invokes
  the skill" and "does not restrict which tools are available". The docs add
  that it is applied even in an untrusted folder, "so review the
  `allowed-tools` of skills checked into a repository".
- `grep -n '^allowed-tools' plugins/*/skills/*/SKILL.md`:
  - 16 of 18 skills list unscoped `Bash`. Only `agent-or-workflow` (read-only)
    and `verify-changes` (no field) do not.
  - 12 of 18 also list `Write` and `Edit`. That includes `settings-review`,
    whose job is review, and `plan-rollout`, whose job is sequencing decisions.
- `plugins/skill-forge/skills/write-a-skill/SKILL.md:44` documents the field as
  "optional: narrows what it may use", the opposite of the docs.
- `plugins/team-rollout/skills/settings-review/SKILL.md` tells users that
  `Bash` alone "grants every command". It then grants itself `Bash`, `Write` and
  `Edit`.
- **Impact.** Every auto-triggered skill turn runs any shell command and any
  file write without a prompt. That covers the 16 skills, which fire on
  ordinary prompts ("kafka", "migration", "settings"). Only the delivery-quality
  guards stand in the way, and they are bypassable (C2). This contradicts
  CONTRIBUTING.md:25 (minimum tools) and `introduction-to-subagents.md:77-82`
  (a reviewer gets read tools plus Bash for diffs, no Edit/Write).
- **Plan:** ROADMAP-v2 Phase 9.1.

#### C2 — The guards miss the common forms of what they block, and the model can disable the secret guard

- **Evidence.** A probe script (`verify/probe.py` in the scratchpad) fed crafted
  payloads to the hook scripts in a temporary git repository. Exit 2 means
  blocked:

  ```
  2  git push origin main --force      (the shape the fixture uses)
  0  git push --force origin main
  0  git push -f origin main
  0  git push origin +main
  2  rm -rf ~/projects                 (the shape the fixture uses)
  0  rm -Rf ~/projects
  0  rm ~/projects -rf
  0  rm -rf $HOME/projects
  2  Write a.py containing an AWS-shaped key
  0  NotebookEdit new_source containing the same key
  0  Write .claude/secret-guard-allow containing ".*"
  0  Write a.py with the same key, once that allow file exists
  ```

- The cause is in `guard_destructive.py`:
  - `:98-102` takes the first word after `push` as the remote.
  - `:76-81` inspects only the first `rm` and only a lowercase `r` in a leading
    flag block.
- The cause is in `guard_secrets.py`:
  - `:113-116` reads only `content`, `new_string` and `command`, never the
    `new_source` field that NotebookEdit sends, although `hooks.json:5` matches
    `NotebookEdit`.
  - Nothing protects `.claude/secret-guard-allow` itself.
  - `:187-188` points the model at that allow file.
- The eval case written to exercise this guard (`guard-blocks-destructive`) can
  only pass if the model happens to put `--force` last. It could not run here
  (§1.5).
- The same guard also over-blocks. During this audit it blocked a heredoc that
  wrote a Python test script, because the heredoc contained `rm -r… ~/projects`
  inside a string literal.
- *(reviewer; the first two re-run by the pre-commit reviewer)* further
  bypasses, not re-run by the auditor:
  - `DROP TABLE` is exempted by any command containing `/dev/` or `developer`.
  - `kubectl delete pods --all` is never matched.
  - A quoted `DELETE FROM users` followed by more arguments passes, e.g.
    `psql -c "DELETE FROM users" -d prod`. The same statement ending in `;` is
    blocked.
- *(tool-schema-review)* The block messages make it worse:
  - Several are written for a human ("run it yourself").
  - The force-push message recommends `--force-with-lease` to the same
    protected branch, which still rewrites the history the message warns about.
  - Following the `reset --hard` advice gets the retry blocked again.
  - Rewrites of every message are in that report.
- **Impact.** The README sells a guard against force-pushing main and deleting
  outside the project. It catches one spelling of each.
- **Plan:** Phase 9.2 and 9.3.

### High

#### H1 — `restore_state.py` injects stale, foreign or untrusted text as measured facts at session start

- **Evidence.**
  1. This audit session opened with a SessionStart context that read "State
     restored after compaction… measured from the working tree". It reported
     branch `main` and a snapshot from the previous day. The real branch was
     `claude/audit-and-fix`, and no compaction had happened.
  2. The file it came from is the repository's `.claude/state/session.md`
     (gitignored). Its header reads "before compaction compaction", and it is
     named `session.md` rather than after a session id. Both are signs of a
     payload with no `trigger` and no `session_id`.
  3. That payload comes from `plugins/context-discipline/tests/run.sh:116`, which
     pipes `not json` into `save_state.py` with no `cwd`. `save_state.py:146`
     then writes `./.claude/state/session.md` into whatever directory the tests
     were started from. This was reproduced: the file appeared in the scratch
     working directory (§1.3).
  4. `restore_state.py:46-53` falls back to the newest `*.md` in the project for
     any session id.
  5. `restore_state.py:109-114` always prints the "restored after compaction"
     header, whatever the event.
  6. `hooks.json:25` registers SessionStart with no matcher, so the hook also
     runs on `startup`, `resume` and `clear`.
- **Untrusted content.** In a scratch clone of a repository that commits
  `.claude/state/notes.md`, a `startup` payload made the hook emit that file's
  text verbatim as `additionalContext`, including an instruction line planted
  in it. The 24-hour staleness filter did not help, because a fresh clone gives
  every file a fresh mtime.
- `save_state.py:116-121` adds the project root's `.claude/handoff.md` with the
  label "written deliberately, trust this over the rest". The assistant writes
  that file through `/handoff`, so the label promotes model-written text.
- `save_state.py:36-41,82`: when git fails or the directory is not a repository,
  the snapshot says "Working tree is clean". Reproduced in §1.3: the leaked
  snapshot reads "Branch: (not a git repo)… Working tree is clean."
- **Impact.** The plugin's purpose is to hand back facts. At startup it hands
  back stale facts, or someone else's text, framed as more trustworthy than the
  conversation.
- **Plan:** Phase 8.1 (test isolation) and 9.4.

#### H2 — The PostCompact half of the design is dead, and the ROADMAP "correction" that chose it is wrong

- **Evidence.**
  - `ROADMAP.md:115` makes PostCompact the primary restore event "because it
    receives the summary".
  - The course says the opposite: `claude-code-in-action.md:108`, `:130`, `:245`
    and the quiz at `:248-253` all say to re-inject after compaction with
    SessionStart and a `compact` matcher.
  - The hooks docs agree. In the decision-control table, PostCompact has no
    decision control and is "used for side effects like logging or cleanup",
    and the list of events whose `additionalContext` reaches Claude does not
    include it. PostCompact does receive `compact_summary` as input, which is
    the part the correction got right.
  - `hooks.json:14` registers `restore_state.py` on PostCompact anyway.
- **Impact.** Restoration after compaction only works by accident: the
  unmatched SessionStart entry also fires with `source: "compact"`. That same
  entry is what causes H1.
- **Plan:** Phase 9.4.

#### H3 — The `audit-skills` command shadows the `audit-skills` skill; the skill body is unreachable

- **Evidence.**
  - `claude plugin details skill-forge@pacoromerodev` lists `audit-skills`
    twice.
  - This session's skill listing carries only the command's one-line
    description, without the skill's "Use when…" triggers.
  - Invoking `skill-forge:audit-skills` through the Skill tool loaded
    `commands/audit-skills.md`, whose body says to use the `audit-skills` skill.
    Invoking it again loaded the same command body. The 61-line procedure in
    `skills/audit-skills/SKILL.md` never loads.
  - The docs' same-name table says a skill beats a file in `.claude/commands/`.
    Inside a plugin, the observed precedence was the reverse. Either way the
    collision has to go.
  - `audit_skills.py` never reads `commands/`, so it cannot see this.
- **Impact.** The skill that exists to find why skills do not fire is itself
  not firing. The `audit-finds-faults` eval passed on prose because the script
  could not run (§1.5).
- **Plan:** Phase 9.5 and 11.2.

#### H4 — The reference managed policy restricts no marketplace, and both templates fail the published schema

- **Evidence.** The templates were validated with `jsonschema` against
  `https://json.schemastore.org/claude-code-settings.json`:

  ```
  managed-settings.json   at strictKnownMarketplaces :: True is not of type 'array'
  project-settings.json   at hooks :: Additional properties are not allowed ('$comment' was unexpected)
  tests/fixtures/good-settings.json   at strictKnownMarketplaces :: True is not of type 'array'
  ```

- The template in detail:
  - `managed-settings.json:35` sets `strictKnownMarketplaces: true`.
  - `managed-settings.json:36` adds `knownMarketplaces`, a key that exists
    neither in the schema nor in the settings reference.
  - The settings reference defines `strictKnownMarketplaces` as an array of
    source objects, where an empty array is a full lockdown.
  - The course note shows the array form too (`introduction-to-agent-skills.md:104-110`).
- The checker misses it. `check_settings.py:104` only tests whether the string
  `strictKnownMarketplaces` appears anywhere in the file, so
  `check_settings.py managed-settings.json --managed` prints
  `Clean — 1 settings file(s), nothing to report.`
- `project-settings.json:20` puts `$comment` inside `hooks`, where the schema
  forbids extra keys. The docs say a rejected value shows a Settings Error and
  the file or entry is skipped.
- **Impact.** ROADMAP.md:210 marks Phase 7 done "when a new machine configured
  from `settings/` reaches a working, restricted setup". Configured from these
  files, it is not restricted.
- **Plan:** Phase 10.

#### H5 — The settings checker does not check the one thing its description leads with

- **Evidence.**
  - The marketplace description promises "a checker for permissions wider
    than intended, unpinned marketplaces and hooks that never fire".
  - `~/.claude/settings.json` registers three third-party marketplaces under
    `extraKnownMarketplaces` (two `github`, one `git`), none with a `ref`.
    `check_settings.py` reports `Clean`, exit 0.
  - The script's only marketplace rule is the managed-file string test above
    (`:103-110`).
  - The docs allow `ref` on `github` and `git` marketplace sources.
  - The model-driven `/settings-check` run did list them, from the skill text
    rather than the script (§3).
- **Plan:** Phase 10.

#### H6 — The eval suite has broken cases and wrong graders

- **Evidence:**
  - `delivery-quality/evals/review-format/` and `verify-not-fired/` hold only
    `prompt.md` and `graders/`, with no scaffold. Every run in both arms found
    an empty working directory. They score 0/0 by construction.
  - The `team-rollout/evals/not-fired` grader has only "score badly if…"
    criteria. The judge failed a correct Shift+Tab answer in both arms, twice
    (the probe and the re-run).
  - The `team-rollout/evals/settings-too-wide` grader wants the credential
    treated as the urgent item. `settings-review/SKILL.md:66` tells the model to
    lead with "anything granting more than intended". The plugin arm followed
    its skill and failed.
  - The `skill-forge/evals/audit-finds-faults` grader rewards "the name does not
    match the directory, so the skill never resolves". For project skills the
    docs say the command comes from the directory and `name` is only a display
    label (docs *Skills → How a skill gets its command name*). See M2.
  - Coverage against CONTRIBUTING.md:94-97, which asks for two positive cases
    and one negative per skill: mapping case tags to skills gives 8 of 18 skills
    with no positive case and none with two. The 8 are `eval-harness`,
    `rag-retriever`, `spring-boot-service`, `java-21-modernize`, `test-shape`,
    `mcp-server-scaffold`, `mcp-roots-check` and `write-a-skill`.
  - `evals.yml:12,18,47`: the weekly schedule evaluates only
    `plugins/delivery-quality`. Its one run failed because the API-key secret
    is missing (§1.4).
- **Impact.** The eval suite cannot currently show any plugin is better than no
  plugin. The two cases that exercise the most safety-relevant component are
  both broken or degraded.
- **Plan:** Phase 8.2 and 12.

#### H7 — Nothing checks the plugins against their own repository

- **Evidence.** This is the dogfooding result (§3), one fact per plugin:
  - **mcp-builder, api-patterns:** there is no MCP server and no API call in the
    repository. This command, over Python, TypeScript and JavaScript files:

    ```
    grep -rlE "FastMCP|mcp\.server|from mcp|import anthropic|from anthropic|messages\.create" \
      --include=*.py --include=*.ts --include=*.js .
    ```

    matches, outside `tests/` and `evals/`, only `check_caching.py`. That file
    is a checker and matches because it contains those strings. Over all file
    types the matches are documentation, skills and checkers; there is no
    `.mcp.json`.
  - **delivery-quality:** `/review` on the clean tree returned an empty but
    correctly formatted report. The test gate cannot gate this repository,
    because it has no runner for `plugins/*/tests/run.sh` and the repo has no
    `.claude/test-gate.*`.
  - **context-discipline:** `claude-md-doctor` has nothing to review; the repo
    has no CLAUDE.md.
  - **skill-forge:** reports the repo clean while H3 stands.
  - **team-rollout:** the checker passes its own templates (H4).
- **Impact.** Every defect above went through CI and the author's own plugins
  unflagged.
- **Plan:** Phases 11 and 15.

### Medium

#### M1 — Skill content contradicted by the course notes

| Plugin claim | Note | What the note says |
|---|---|---|
| `eval-harness/SKILL.md:98-104`: in the 2.3 → 3.9 → 7.9 progression, the jump to 7.9 "comes from examples… not from more adjectives" | `claude-with-the-anthropic-api.md:236`, `:245`, `:806` | 2.32 → 3.92 came from a clear first line; 3.92 → 7.86 came from a list of specific output guidelines. Examples are taught afterwards, with no score reported |
| `rag-retriever/SKILL.md:88-91`, contextual-retrieval prompt | `claude-in-amazon-bedrock.md:135-144` | The situating call receives the document (or its opening chunks plus the preceding ones) **and** the chunk. The skill's template passes only `<chunk>`, so the model has nothing to situate it in. Its wording is also close to the course prompt (see *Go-public* in ROADMAP-v2) |
| `choose-transport/SKILL.md:35-44,63` lists what stateless mode removes; its pre-switch grep looks for `create_message`, `report_progress`, `subscribe`, `ctx.info` | `model-context-protocol-advanced-topics.md:143`, `:170-176` | List Roots is a server-initiated request too. `mcp-roots-check` depends on `list_roots()`, which the grep and the list both omit |
| `choose-transport/SKILL.md:55`: `json_response=True` "costs only incremental delivery" | same note `:146`, `:165`, `:178` | It removes progress and intermediate logs as well |
| `choose-transport/SKILL.md:43`: stateless also loses logging callbacks | same note `:146`, `:163`, `:165`, `:170-176` | The note is ambiguous. `:146` and `:165` say the restrictive flags, together, remove logs. `:163` routes logs over the per-call stream, and `:170-176`, listing what `stateless_http` alone loses, omits them. Settle it against the SDK before changing either the skill or the `stateless-tradeoff` grader |

**Plan:** Phase 13.

#### M2 — Skill content contradicted by current Claude Code or API documentation

| Claim | Where | Current source |
|---|---|---|
| Caching is "never automatic" | `prompt-cache-audit/SKILL.md:9`, `check_caching.py:7,119-121`; the note too (`claude-with-the-anthropic-api.md:594`) | API docs: a top-level `cache_control` enables automatic caching, which moves the breakpoint forward |
| A prefix "under about 1024 tokens" is not stored; smaller models have a higher floor | `prompt-cache-audit/SKILL.md:27-28`, `check_caching.py:31` | Minimum is model-specific, from 512 (Opus 5) to 4,096 (Haiku 4.5, Opus 4.5/4.6) |
| One-hour cache TTL | `ROADMAP.md:188`; the note says so too (`claude-with-the-anthropic-api.md:590`, `:793`, `:815`) | Default is 5 minutes. 1 hour is opt-in (`ttl: "1h"`) at twice the write price. The skill itself avoids a number |
| `cache-on-tail` warns against a breakpoint on the newest message | `check_caching.py:173-181` | Automatic caching puts the breakpoint on the last cacheable block. The note does not back the warning (`:598`) |
| A skill whose `name` ≠ directory "does not resolve" | `audit-skills/SKILL.md:30`, `write-a-skill/SKILL.md:35`, the `audit-finds-faults` grader | Docs: in project and personal skills the command comes from the directory and `name` is a display label. The note (`introduction-to-agent-skills.md:48`, `:70`) states the open-standard rule, which is a portability concern, not a load failure |
| That `name` and `description` are both mandatory | `write-a-skill/SKILL.md:49` | Claude Code docs: `name` optional (defaults to the directory), `description` recommended. The listing truncates description plus `when_to_use` at 1,536 characters |
| Subagents do not inherit skills; built-ins cannot use skills | `write-a-skill/SKILL.md:120-121`; note `introduction-to-agent-skills.md:113-117` | Docs: `skills:` preloads, but subagents can still invoke unlisted skills through the Skill tool. Built-in agents do not preload |
| An invalid settings file is ignored "silently… with no message anywhere" | `settings-review/SKILL.md:55` | Docs: an interactive session shows a Settings Error dialog |

Where the note itself is out of date (caching, subagent skills), the plan
cites the note for the concept and the docs for the number.

**Plan:** Phase 13.

#### M3 — `${CLAUDE_PLUGIN_ROOT}` in skill prose is rewritten on load

`settings-review/SKILL.md:48` advises "Use `$CLAUDE_PROJECT_DIR` or
`${CLAUDE_PLUGIN_ROOT}`". Claude Code substitutes the variable in skill
content (docs, *Skills → string substitutions*), and the rendered skill in this
session read "…or `<absolute install path>/plugins/team-rollout`". The
model is told to recommend *this plugin's* install path for the user's own
hooks. **Plan:** Phase 13.

#### M4 — CI gaps, some of which leave the eval workflow unsafe

Evidence is in §1.6, plus the workflow itself:

- `evals.yml:47,52` interpolate `${{ inputs.* }}` straight into `run:`.
- The workflow has no `permissions:` block.
- `actions/checkout` keeps the token in `.git/config`, and the job then runs a
  model with `--allow-tools Bash --scaffold --trust-plugin`.
- Both workflows install `@anthropic-ai/claude-code` unpinned.

*(reviewer)* The 3.8 matrix leg depends on `ubuntu-latest` still offering 3.8.
**Plan:** Phase 11.

#### M5 — Test-gate defects *(reviewer; the parse failure reproduced by the reviewer, the rest read from code)*

- `test_gate.py:23` parses `CLAUDE_TEST_GATE_TIMEOUT` at import time, outside
  the fail-open wrapper. A value like `15m` exits 1 with a traceback.
- `:180-182` accepts a project timeout above the hook's own 960 s
  (`hooks.json:31`). Claude Code kills the hook first, and its "timed out"
  feedback never prints.
- `only_when_changed` ignores changes that were already committed.
- The hook docstring says it runs "before the session is allowed to end".
  `Stop` fires at the end of every turn.
- `README.md` says a timeout lets the session end, but `test_gate.py:189-193`
  returns 2.
- *(tool-schema-review)* After one block, the next stop carries
  `stop_hook_active` and the gate exits 0 without re-running. The fix it
  demanded is never checked. The hooks docs already cap consecutive Stop
  blocks, so the short-circuit buys nothing.

**Plan:** Phase 9.6.

#### M6 — `guard_destructive` false positives *(reviewer, reproduced for the heredoc case)*

- `reset --hard` and `checkout .` are blocked when the only change is an
  untracked file, because `git status --porcelain` counts untracked files. The
  hook suite's own `.claude/state/` output is exactly such a file.
- Dangerous-looking text inside quoted strings and heredocs is blocked (C2).
- `git clean -nd`, a dry run, is blocked.
- *(tool-schema-review)* `guard_secrets` never reads `tool_name`:
  - It blocks read-only searches such as `grep -rn <key> src/`, because it
    scans the whole Bash command as if it were written to disk.
  - Its path rule blocks committed templates such as `.env.example`.

**Plan:** Phase 9.2 and 9.3.

#### M7 — The handoff note never reaches a fresh session *(reviewer)*

`/handoff` writes `.claude/handoff.md`, and `/context` recommends `/handoff`
then `/clear`. But `restore_state.py` never reads the live file. The note only
travels frozen inside a PreCompact snapshot (`save_state.py:114-127`), so after
`/clear` with no compaction it is lost, and after an old compaction the stale
copy wins. **Plan:** Phase 9.4.

#### M8 — Content in the notes that the plugins claim but do not deliver

| Plugin | Gap | Note |
|---|---|---|
| team-rollout | Connectors are half of the Access decision: three gates (org, role, member), read versus write with sign-off by the risk owner, IdP-provisioned authorisation. `plan-rollout` mentions connectors only inside the union rule | `deploying-claude-enterprise-with-confidence.md:129-148` |
| team-rollout | Setting the deployment objective (success plus constraints) before any setting. Who owns each decision; spend and visibility usually escalate beyond the Owner | same note `:30`, `:35-48` |
| team-rollout | Spend levers other than limits (default model, effort cap, organisation instructions, scheduled tasks); overrides multiplying means a group is missing | same note `:186`, `:198-202` |
| context-discipline | `claude-md-doctor` has nothing on hard rules belonging in a PreToolUse hook rather than CLAUDE.md, or on starting without a CLAUDE.md and adding rules only for corrections actually repeated | `claude-code-in-action.md:36`, `:53`; `claude-code-101.md:114` |
| context-discipline | Placement: critical rules first and repeated at the end, because the middle of a long context loses attention | `ai-capabilities-and-limitations.md:126-132` |
| delivery-quality | PostToolUse lint/type-check after each edit; redacting a secret through `updatedInput` rather than blocking | `claude-code-in-action.md:120`, `:128`, `:190` |
| delivery-quality | Checking that packages the model introduces actually exist | `ai-fluency-for-builders.md:40` |
| skill-forge | Evals comparing each skill with and without it, 1–2 rounds, stopping when clearly better than baseline — the bar `write-a-skill` should set | `introduction-to-claude-cowork.md:168-177` |
| skill-forge | Subagent authoring: the description shapes the prompt the parent writes when delegating; nothing audits `agents/*.md` | `introduction-to-subagents.md:65-68`, `:70-82` |
| api-patterns | Generating the dataset with a fast model; reusing top-scored outputs as few-shot examples | `claude-with-the-anthropic-api.md:163`, `:278` |
| api-patterns | Build path for an agent: own loop, tool runner or managed agents | `claude-platform-101.md:119-130`, `:316-317` |
| api-patterns | Thinking incompatibilities (prefill, temperature), minimum budget, `effort` inside `output_config` | `claude-with-the-anthropic-api.md:527`, `:543`; `claude-platform-101.md:136` |
| api-patterns | Bedrock and Vertex deltas (`converse`, `toolChoice`, `toolResult.status`, inference profiles, Model Garden, ADC), promised by ROADMAP.md:193 | `claude-in-amazon-bedrock.md:23-73`; `claude-with-google-vertex.md:12-23` |
| mcp-builder | Test with the transport production uses | `model-context-protocol-advanced-topics.md:184` |

**Plan:** Phases 13 and 14.

#### M9 — ROADMAP marks phases done whose done-criteria are not met

| ROADMAP line | Claim | State |
|---|---|---|
| `:40` | 0.1 verified "by pushing a deliberately broken branch once" | No branch or PR run in CI history (§1.4) |
| `:60` | 0.3 baseline arm "visibly differs" | Of 10 valid positive cases, 7 tie and 1 loses (§1.5) |
| `:115` | PostCompact is the primary restore event | Wrong (H2) |
| `:187` | `eval-harness` is "Skill + `scripts/`" | `eval-harness/SKILL.md:107` says it ships no runner on purpose. The `scripts/` directory holds `check_caching.py` and `fuse.py` only |
| `:193` | Bedrock/Vertex deltas in `references/` | Absent: `eval-harness/references/` holds only `graders.md` |
| `:207-208` | `docs/rollout.md`, `docs/plugin-trust.md` | Neither file exists anywhere in the repository |
| `:210` | 7 done: restricted setup from `settings/` | False (H4) |

**Plan:** ROADMAP-v2 records the correction.

#### M10 — Trigger collisions between installed plugins

The auditor's overlap rule is lexical (`audit_skills.py:248-263`: more than
60% shared words of four or more letters) and reports all 18 clean. It only
ever compares `SKILL.md` files, never agents, commands or built-ins. The
`skill-describer` run (§3) found three semantic collisions:

- **"Why isn't my skill firing?"** matches four components: `write-a-skill`,
  the `audit-skills` skill, the `/audit-skills` command and `skill-describer`.
  `write-a-skill`'s own description is almost a paraphrase of the
  `description-rewrite` eval prompt, which is meant for `skill-describer`.
- **"Claude never calls my tool"** matches both `tool-schema-review`
  (api-patterns) and `mcp-review` (mcp-builder). Neither description says
  where the tools are defined, so `tool-schema-review` also matches
  mcp-builder's own `tool-never-called` eval.
- **"Double-check this before I commit"** is claimed by `verify-changes`, by
  `code-reviewer` and by the built-in `/code-review`. `code-reviewer`'s
  description ("use proactively before a commit", "a check of what was just
  written") contradicts `delivery-quality/README.md:13-14`, which gives it only
  reviews and second opinions.
- Separately, `test-shape` never says Java or Spring in its description,
  although its body is Spring-only, so it competes in any repository.
- Name pairs: mcp-builder ships a `mcp-review` command and a `mcp-review`
  agent (`claude plugin details` lists both). No failure was observed, since
  agents and skills resolve through different tools, but it is the same
  pattern as H3.

The describer's recommended rewrites are the starting point for Phase 13.
**Plan:** Phase 11.2 and 13.

#### M11 — `/context` asks for evidence the model cannot obtain

`commands/context.md` asks for "the evidence: what is actually taking up
room". Run in this session, the model had only a budget counter, not the
per-category fill that the built-in `/context` shows. A plugin command cannot
read that output. The report it produced was an estimate, and said so.
**Plan:** Phase 13.

#### M12 — `check_stdlib_only.py` allows a module the supported Python lacks *(reviewer; confirmed by grep)*

`check_stdlib_only.py:23` allows `tomllib` (3.11+), while CI still tests 3.8.
An import would pass CI and crash the hook on 3.8–3.10. `grep -n tomllib
plugins/*/scripts/*.py` finds no import today. **Plan:** Phase 11.

#### M13 — The hooks take the project root from `CLAUDE_PROJECT_DIR`, not the payload's `cwd` *(tool-schema-review; reproduced by that agent; confirmed in code)*

- **Evidence.** Four scripts put `CLAUDE_PROJECT_DIR` first and fall back to
  the stdin `cwd` (e.g. `restore_state.py:26-34`). `guard_secrets.py:92` reads
  only `CLAUDE_PROJECT_DIR`. The
  hooks docs define `CLAUDE_PROJECT_DIR` as the directory where the session
  *started*, and say the input `cwd` follows Claude into worktrees and after
  `cd` (hooks docs, *Reference scripts by path*).
- **Impact.** In a worktree:
  - `test_gate` tests the clean main checkout and passes a regression.
  - `guard_destructive` runs `git status` in the wrong tree, so it allows
    `reset --hard` over real changes.
  - The guard resolves relative `rm` targets against the wrong directory.
  - `save_state` snapshots the wrong tree as "measured facts".
- **Plan:** Phase 9.7.

#### M14 — Hook output has no size bound *(tool-schema-review)*

- **Evidence.**
  - A snapshot with 45 changed files, 5 commits and a 60-line handoff note
    produced 16,341 characters of `additionalContext`. Above 10,000, Claude
    Code writes the text to a file and shows a 2,000-character preview, which
    cuts off before the handoff note.
  - `test_gate` keeps 20 or 40 lines with no character cap. One long failure
    line produced about 300,000 characters of stderr for the model.
  - Both guards echo paths and targets verbatim.
- **Plan:** Phase 9.4 and 9.6.

#### M15 — Failure paths nobody sees *(tool-schema-review; cross-checked against the hooks docs)*

- `test_gate` writes "enabled but no test runner was found" and
  "could not run" to stderr on exit 0. For Stop that reaches only the debug
  log, so a project that opted in can silently lose its gate. A config value
  of the wrong type does the same with no message at all.
- `save_state` prints a `systemMessage`, which PreCompact discards.
- The guard matchers miss the `PowerShell` tool (Windows without Git Bash)
  and MCP file-writing tools.
- `guard_secrets.py:123-124` handles an `edits[]` list, which is
  MultiEdit-shaped. No MultiEdit tool is in the matcher or the current docs,
  and `tests/fixtures/edge-multiedit.json` sends that shape under
  `tool_name: "Edit"`, a payload Edit does not produce.
- **Plan:** Phase 9.3 and 9.6.

#### M16 — `verify-changes` cannot see a change made of new files, or this repository's tests

- **Evidence.** Run as written on the two new files of this audit (§3):
  - Step 1's runner table found nothing. It has no entry for
    `plugins/*/tests/run.sh`, so no test ran.
  - Steps 2 and 3 use `git diff HEAD`, which returned 0 lines, because
    untracked files are not in it. The skill's own report would then read
    "Diff: 0 files".
- **Impact.** A change that adds a new file — a new test, a new module, a file
  with a secret — passes through the verification step unread. The same holds
  for `code-reviewer`'s default scope (`git diff HEAD`), which is why the
  pre-commit review here had to be scoped by hand.
- **Plan:** Phase 13.14.

### Low

- **L1** `save_state.py:54,66`: with no `trigger`, the header reads "before
  compaction compaction".
- **L2** `README.md`'s delivery-quality table lists four components and omits
  `guard_destructive` (`grep -c guard_destructive README.md` → 0).
- **L3** Commands are thin wrappers that each cost always-on tokens (§1.2) and
  add a second entry for the same trigger. `/verify` and `verify-changes` both
  appear in the listing.
- **L4** The suite mixes `case.yaml` and the older `prompt.md` form. The only
  two `prompt.md` cases are the broken ones (H6).
- **L5** `check_consistency.py:46` skips a plugin directory that has no
  `plugin.json`, silently *(reviewer)*.
- **L6** `README.md:12` still describes the repository as private.
- **L7** `write-a-skill/SKILL.md:16` sends the model to `docs/anatomy.md`. That
  file is at the repository root, and the installed plugin
  (`~/.claude/plugins/cache/pacoromerodev/skill-forge/0.1.0/`) has no `docs/`
  directory.

---

## 3. Dogfooding: the toolkit run on its own repository

| Tool | Target | Result |
|---|---|---|
| `/audit-skills` (skill-forge) | the 18 real `SKILL.md` | The command loads; the skill it delegates to cannot (H3). The script reports all 18 clean. It misses C1 (no `allowed-tools` rule), H3 (never reads `commands/`), M2 (encodes the stale rules) and M10 (lexical overlap only) |
| `skill-describer` (skill-forge) | the three strongest trigger collisions: "skill not firing", "tool never called", "check before commit" | Three candidate sets, each with prompts it would and would not match, and a recommendation (M10). It found that the auditor never compares agents, commands or built-ins at all. It also found that `code-reviewer`'s description contradicts the plugin README's split, and that `write-a-skill` cites a file the installed plugin does not ship (L7) |
| `/settings-check` → `settings-review` (team-rollout) | `settings/*.json`, `~/.claude/settings.json` | The script reports all three clean, including the `--managed` run. The skill-driven review found what the script cannot see: the unpinned marketplaces (H5) and, once validated against the schema, H4. The rendered skill showed M3 |
| `/context` (context-discipline) | this session | Recommended "keep going" with a correct compaction plan, but on estimated evidence (M11) |
| `claude-md-doctor` (context-discipline) | no CLAUDE.md in the repo | The skill has no path for "should this repo have one". Decision: yes, short, and only rules that map to commands. A 26-line draft passed `check_claude_md.py` with `Clean — 26 lines, nothing to report.` Phase 15 carries it |
| `/review` (delivery-quality) | clean tree | Correct empty report: all headings kept, "Obstacles encountered" explains that there is no diff and what scope would work |
| `/review` with scope (delivery-quality) | hook scripts and CI files | 4 blocking, 12 worth fixing, 13 noted, all anchored to file:line with the failing input. The four blocking items were re-run by the auditor and hold (C2). Its "Obstacles" section named what it assumed from docs |
| `/review` (delivery-quality) | this audit's two files, before commit | The default scope saw nothing, because both files were untracked (M16), so the scope was given explicitly. It spot-checked about 60 repository citations and about 50 note citations and re-ran several measurements; the Critical and High evidence held. It returned 3 blocking and 13 worth-fixing items against the documents themselves: an unfilled placeholder, a statistic that did not match its own table (now 8 of 10), an eval-workflow run that happened mid-audit (§1.4), and several done-criteria in ROADMAP-v2 that could not fail. All are corrected in the committed version |
| `/verify` → `verify-changes` (delivery-quality) | the same two files | Run as written: no runner detected, and `git diff HEAD` showed 0 lines. Verdict per its own format: *not verified*. The skill cannot see a change that consists of new files (M16) |
| `tool-schema-review` (api-patterns) | the five hook scripts and both `hooks.json` (an off-label use: hooks, not API tools) | A per-hook contract table (stdin fields, exit codes, what reaches the model) and full rewrites of every block message. It found M13, M14 and M15, and corrected one reviewer claim: there is no double injection after compaction, only a dead PostCompact registration (H2). Its own verdict on fit: its failure-behaviour, parameter and result-size questions carried over. "Would the model pick it" did not, because the harness picks hooks, and the largest findings came from event semantics in the harness docs, which a schema reviewer does not read |
| `mcp-review`, `/mcp-new`, `choose-transport`, `mcp-roots-check` (mcp-builder) | — | Not applicable: no MCP server in the repository (H7). The plugin is exercised only by its own fixtures |
| `prompt-cache-audit`, `eval-harness`, `rag-retriever`, `agent-or-workflow` (api-patterns) | — | Not applicable: no code calls the Claude API (H7) |
| java-spring | — | Not applicable: no Java in the repository. Its evals are its only exercise |
| Hooks (delivery-quality, context-discipline) | this session | `restore_state` injected the stale snapshot (H1). `guard_destructive` blocked one legitimate heredoc (C2). `test_gate` stayed inert: no marker file |

---

## 4. Content audit against the notes

Per plugin, sources as in the ROADMAP Source map plus any other note that
bears on it. "Backed" means the note states the concept, cited by line.

**delivery-quality.** Backed:
- a verification skill that runs tests, reads the diff and checks for weakened
  tests (`claude-code-in-action.md:55-64`);
- exit 2 as the only blocking code (`:122-126`, `claude-code-101.md:165-168`);
- a cold read-only reviewer (`introduction-to-subagents.md:91`, `:117-118`,
  `claude-code-101.md:95-96`);
- output format and Obstacles section (`introduction-to-subagents.md:70-75`);
- a Stop hook with tests as the correctness gate (`claude-code-in-action.md:94`,
  `:190`).

Not implemented: M8 rows. Contradicted: none by the notes; C2 and M5 are
defects against the plugin's own claims.

**context-discipline.** Backed:
- compaction with instructions, rewind, `/clear` and `/context`
  (`claude-code-in-action.md:17-23`, `claude-code-101.md:82-93`);
- explore, plan, code, commit (`claude-code-101.md:69-80`);
- CLAUDE.md as guidance, specific and checkable rules, naming the alternative,
  emphasis as a budget, imports not saving context
  (`claude-code-in-action.md:33-53`).

Contradicted: the PostCompact design (H2). Not implemented: `/goal` as a
verifiable completion condition (`:26`), except as prose in `scope-task`;
M8 rows.

**skill-forge.** Backed:
- only the description loads at startup, and it answers what and when
  (`introduction-to-agent-skills.md:51-55`, `:75`);
- progressive disclosure and scripts that are run, not read (`:79-86`);
- under 500 lines (`:84`);
- the troubleshooting order (`:123-130`).

The skill states the note's open-standard constraints as Claude Code load
failures (M2). Not implemented:
- precedence and shadowing (`:57-63`, `:128`), the gap H3 fell into;
- the agent-skills validator (`:124`);
- auditing `agents/*.md` (M8).

**mcp-builder.** Backed:
- the three primitives by controller (`introduction-to-model-context-protocol.md:169-178`);
- direct and template resources (`:111-124`);
- Inspector (`:75-84`);
- sampling and its callback (`model-context-protocol-advanced-topics.md:11-53`);
- roots not enforced by the SDK (`:91`);
- stateless losses (`:170-176`).

Contradicted or unbacked: M1 rows. Not implemented: client side
(`introduction-to-model-context-protocol.md:86-101`, deliberately out of scope)
and testing on the production transport (`:184`).

**api-patterns.** Backed:
- evaluation pipeline, code graders at 10 or 0, reasoning before score to
  avoid the flat 6 (`claude-with-the-anthropic-api.md:150-211`);
- caching order, four breakpoints, byte-identical prefix (`:593-624`);
- BM25, RRF with k around 60 (`:494-524`);
- reranking by id (`claude-in-amazon-bedrock.md:125-133`);
- workflow versus agent and the four patterns
  (`claude-with-the-anthropic-api.md:691-766`);
- model choice from the cheapest up (`claude-platform-101.md:62-68`).

Contradicted: M1, M2. Not implemented: M8 rows. Extended thinking, citations,
Files API and code execution (`claude-with-the-anthropic-api.md:526-648`) have
no component.

**team-rollout.** Backed:
- the five decisions in order and the four that are hard to undo
  (`deploying-claude-enterprise-with-confidence.md:15-26`);
- prerequisites (`:59-73`), topology (`:75-88`) and the union rule (`:99`);
- surfaces with two gates (`:110-113`);
- governance controls and postures (`:158-175`);
- spend with pause at limit and the multi-group rule (`:178-193`);
- visibility, retention minimum and adoption signals (`:220-256`);
- new-product questions (`:270-273`).

Not implemented: M8 rows. The `plan-rollout` worked example
(`SKILL.md:144-147`) follows the note's fictional-company example
(`:275-276`) closely — concept reuse, flagged for the go-public wording check.

**java-spring.** By design not sourced from the notes (ROADMAP.md:147). The
notes back only its shape: specific, checkable rules
(`claude-code-in-action.md:48-51`) and a reviewer with fixed output and minimal
tools. Nothing in the notes contradicts it. Its content was not audited against
external Spring or Kafka documentation (*Not verified*).

---

## 5. Coverage: 22 courses × 7 plugins

**P** = listed in the Source map and implemented. **I** = implemented but not
listed. **–** = not used.

| Course (`web/src/…`) | DQ | CD | SF | JS | MB | AP | TR | Decision |
|---|---|---|---|---|---|---|---|---|
| claude-code-in-action | P | P | I | I | – | – | I | Covered. Unattended runs (`:132-192`) enter delivery-quality as a workflow checker (Phase 14.2); redaction via `updatedInput` enters the secret guard (14.3). Worktrees and `/goal`: no tool — built-in features with nothing to check |
| claude-code-101 | I | P | I | – | – | – | – | Covered; two rules enter `claude-md-doctor` (M8) |
| introduction-to-agent-skills | – | – | P | – | – | – | I | Covered; precedence and `allowed-tools` enter the auditor (9.1, 11.2) |
| introduction-to-subagents | P | – | I | I | I | I | – | Covered in shape; an **agent auditor** enters skill-forge (14.1) |
| introduction-to-model-context-protocol | – | – | – | – | P | – | – | Covered. Client side: no tool — application-specific, and the plugin is deliberately server-side |
| model-context-protocol-advanced-topics | – | – | – | – | P | – | – | Covered; corrections in 13 |
| claude-with-the-anthropic-api | – | – | – | – | I | P | – | Covered; thinking and prefill checks enter an API-call checker (14.4); dataset generation enters `eval-harness` (13) |
| claude-platform-101 | – | – | – | – | – | P | – | Partly; build-path decision enters `agent-or-workflow` (13); `effort` placement enters the API-call checker (14.4) |
| claude-in-amazon-bedrock | – | – | – | – | – | P | – | Partly; provider deltas become a `references/providers.md` with an eval (14.5). Computer use: **no tool** — it needs sandbox infrastructure, and nothing in a repo can be checked. Production-debugging Action: folds into 14.2 |
| claude-with-google-vertex | – | – | – | – | – | – | – | **Skill in api-patterns**: same providers reference (14.5). Everything else duplicates the API course |
| deploying-claude-enterprise-with-confidence | – | – | – | – | – | – | P | Covered; connectors, objective and spend levers enter `plan-rollout` (13) |
| introduction-to-claude-cowork | – | – | – | – | – | – | – | **No tool** for Cowork itself (a desktop surface, no artefact in a repo). Its skill-eval lesson (`:168-177`) enters skill-forge as the bar for evals (12, 13) |
| claude-101 | – | – | – | – | – | – | – | **No tool.** End-user product surfaces (Projects, Artifacts, Research). No repository artefact to generate or check |
| ai-capabilities-and-limitations | – | – | – | – | – | – | – | **No own tool.** One rule enters `claude-md-doctor`: placement of critical rules (`:126-132`), checked by `check_claude_md.py` on long files (13) |
| ai-fluency-for-builders | – | – | – | – | – | – | – | **Skill content in delivery-quality**: package-existence check in `verify-changes` (`:40`), and a "does it meet the stated acceptance criteria" lens in `code-reviewer` (`:56`, `:83-90`) (14.6) |
| ai-fluency-framework-foundations | – | – | – | – | – | – | – | **No tool.** The 4D vocabulary describes human judgement; it has no executable form, and prompting technique is already covered by the API course |
| ai-fluency-for-creative-work | – | – | – | – | – | – | – | **No tool.** Decisions about creative practice and disclosure; nothing runs in a code repository |
| ai-fluency-for-educators | – | – | – | – | – | – | – | **No tool.** Course design; no repository artefact |
| ai-fluency-for-students | – | – | – | – | – | – | – | **No tool.** Study practice and career preparation |
| ai-fluency-for-nonprofits | – | – | – | – | – | – | – | **No tool.** Organisational AI policy. A policy generator would produce the generic text the course warns against, with no mechanical check. Its one executable idea — validate on data with a known answer (`:67-73`) — is already in `eval-harness` |
| ai-fluency-for-small-businesses | – | – | – | – | – | – | – | **No tool.** Same reasoning; the "should AI do it" triage is already `agent-or-workflow` |
| teaching-ai-fluency | – | – | – | – | – | – | – | **No tool.** Pedagogy of the framework |

**No new plugin.** No uncovered course yields a component that does work and
cannot live in an existing plugin. The evidence also argues against adding one:
- the seven already cost ~2,921 always-on tokens;
- they collide on triggers (M10);
- in 8 of 10 valid positive cases they did not beat the baseline (§1.5).

The unattended-runs material was the strongest candidate for a plugin of its
own. It goes into delivery-quality instead, because its core — verifying work
nobody watched — is that plugin's stated purpose, and this repository's own
`evals.yml` is the first target it would catch (M4).

---

## Not verified

- **Bash-dependent eval behaviour.** 11 `case.yaml` files list Bash. Four
  were visibly degraded without it (§1.5); the other seven passed or failed on
  reading alone, so their Bash paths were never exercised. The Docker
  credential-store symlink blocks Bash-granting evals on this machine, and the
  auditor did not work around the check. Until the store is a plain directory,
  those paths are unmeasured.
- **Run-to-run variance.** Every case ran once per arm. A single flip changes
  any delta shown.
- **Settings behaviour at runtime.** Whether Claude Code 2.1.274 skips the
  whole managed file or only the rejected entry for `strictKnownMarketplaces:
  true` was not observed; H4 rests on the schema and the settings reference.
- **Command-versus-skill precedence as documented.** The docs cover
  `.claude/commands` against skills, not a plugin's `commands/` against its own
  `skills/`. H3 rests on observed behaviour in 2.1.274 only.
- **PostCompact output being discarded.** H2 rests on the hooks docs and the
  course note. No compaction was triggered to observe it.
- **CI's Python 3.8 leg and shellcheck.** Neither is installed locally; their
  status comes from the GitHub run history only.
- **The GitHub side of M4.** The repository's default `GITHUB_TOKEN` permission
  was not inspected.
- **Employer-term scan** (go-public item 1). Only the owner knows the terms. A
  grep for company names that appear in the notes found none, which proves
  nothing.
- **Verbatim-copy check** (go-public item 3). Beyond the `rag-retriever` prompt
  (M1), no systematic comparison of plugin text with the notes' English code
  blocks was run; Phase 11.4 builds one.
- **java-spring content correctness.** Not checked against Spring or Kafka
  documentation.
- **The mcp-builder scaffold under the Inspector** (ROADMAP Phase 5
  done-criterion). The `mcp` package is not installed; not attempted.
- **Subagent findings not re-run by the auditor.** These are marked
  *(reviewer)* or *(tool-schema-review)*: part of C2's secondary list, M5
  except the parse failure, M6 except the heredoc case, M7, M13 to M15, and
  L5. Both agents report running the scripts on crafted payloads in temporary
  directories, and their probe scripts are kept in the audit scratchpad. The
  auditor re-ran only the eight bypasses in C2.
