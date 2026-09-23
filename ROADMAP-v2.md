# Roadmap — second iteration

This continues [`ROADMAP.md`](ROADMAP.md). The Source map, phases 0–7 and the
"Before making this repository public" checklist stay where they are; phases
here are numbered from 8. Every item comes from a finding in
[`AUDIT.md`](AUDIT.md) (IDs such as C1 or H3), from a course note
(`<course>.md:<line>`, paths relative to the academy repo's `web/src/`), or
from both.

**The rule for this plan:** a change enters only with a way to verify it. Each
item names what changes, what backs it, a done-criterion stated as a command
and its expected result, and the test or eval that keeps it done. Anything
that cannot be checked is listed under *Excluded*.

---

## Status — 2026-09-23

Every phase is implemented, one commit per item and one pull request per
phase, stacked in the order the work was done. CI is green on every one of
them, including the Python 3.8 leg.

| Phase | Pull request | Done-criterion |
|---|---|---|
| 8 | pacoromerodev/claude-code-toolkit#2 | Met. Suites run from a sandbox; a fresh worktree stays clean after all seven |
| 9 | pacoromerodev/claude-code-toolkit#3 | Met. Re-running AUDIT C2's probe: all eleven rows now exit 2. A key still passes once the user writes an allow file of `.*` — the model can no longer write that file, which was the defect |
| 10 | pacoromerodev/claude-code-toolkit#4 | Met, except the manual refusal on a managed machine (see *Not automatable*) |
| 11 | pacoromerodev/claude-code-toolkit#5 | Met. The broken branch was pushed and failed: pacoromerodev/claude-code-toolkit#6 |
| 13 | pacoromerodev/claude-code-toolkit#7 | Met, except 13.7's live routing run (below) |
| 14 | pacoromerodev/claude-code-toolkit#8 | Met |
| 15 | pacoromerodev/claude-code-toolkit#9 | Met. `check_claude_md.py CLAUDE.md` is clean, and CI runs it |
| 12 | pacoromerodev/claude-code-toolkit#10 | Coverage met (`--enforce` exits 0). The per-plugin bar is met by three of seven; see the results below |

**Order.** Phases 13 and 14 were done before 12. Every row of both carries an
eval case, and those cases are Phase 12's coverage; writing them first meant
writing each case once.

### Where the work departed from this plan

- **9.1 is stricter than written.** No skill pre-approves `Write` or `Edit`,
  including the scaffolders the plan would have allowed to keep them. File
  changes go through the normal permission prompt everywhere.
- **11.4 ships hashes, not a checkout.** The academy repository is private, so
  CI cannot clone it. `data/course-shingles.txt` holds 350 truncated hashes and
  no text. The window is five words with a content-word floor, not eight: eight
  missed the one passage the audit found, and five alone flagged a stock phrase
  in six descriptions.
- **11.6 kept the 3.8 floor** — a hook uses whatever `python3` is installed,
  and a stock macOS answers 3.9 — and pinned that leg to `ubuntu-24.04`, since
  no 3.8 build exists for 26.04.
- **13.11 and 13.12 renamed two commands** the plan kept: `/review` became
  `/review-diff` and `/context` became `/context-budget`. Both short names are
  commands Claude Code ships, which `check_names.py` (11.2) found once its
  built-in list was read from the documentation.
- **13.13's criterion could not be met as written.** `grep -ci private
  README.md` counts "private keys" in the list of credentials the guard blocks.
  The criterion that holds is that no sentence claims the repository is
  private.
- **13.6's criterion** asked that `${CLAUDE_PLUGIN_ROOT}` appear only on
  invocation lines. It also appears once in prose, saying what it is not for.
- **13.12's token drop is mostly 9.1's.** 2,921 → 2,011 always-on tokens. The
  projection counts the frontmatter, so narrowing `allowed-tools` took about 30
  tokens off every skill; deleting the eight wrapper commands is the rest.
- **Several claims were settled against the live documentation or the SDK
  rather than the notes,** which had gone stale: automatic caching and the
  per-model minimum (13.4), what stateless mode and `json_response` each drop
  (13.3, against the MCP Python SDK), which frontmatter fields are required and
  where descriptions are truncated (13.5), what a broken settings file does
  (13.6), and that `updatedInput` replaces the tool input rather than merging
  (14.3).

### Not done here, and why

- **13.7's live routing run.** `scripts/route_check.sh` needs a logged-in CLI
  with this branch's plugins installed. A throwaway config answers "Not logged
  in", and installing a branch into the owner's own configuration is not this
  work's to do. The script is tested against a stub in CI; the live run is a
  release step.
- **The `ANTHROPIC_API_KEY` secret.** `gh secret list` is empty, so the weekly
  eval workflow stops at its own check. Only the repository owner can add it.
- **Eighteen of the 53 eval cases.** `claude plugin eval` refuses a
  Bash-granting run while the Docker credential store holds a symbolic link,
  as it does on the machine this ran on, so every case tagged `needs-bash` was
  skipped and listed as NOT RUN. That includes seven of delivery-quality's
  eight, which is to say the whole of its measurable surface: the guards, the
  gate and the two Phase 14 lenses. They run in CI once the secret exists.

---

## Why the order

```
Phase 8  honest measurement ──> Phase 9  safety defects ──┬─> Phase 11 CI gates ──> Phase 12 eval coverage
                                Phase 10 settings ────────┘                               │
                                                          Phase 13 content ──────────────┤
                                                          Phase 14 new components ───────┤
                                                                                          └─> Phase 15 repo CLAUDE.md
```

- **Phase 8 comes first.** Today the fixture tests pollute the repository, and
  a third of the eval cases are broken or degraded. Any later "done" measured
  with them would repeat ROADMAP.md's mistake of calling phases done on
  measurements that could not fail (AUDIT M9).
- **Phases 9 and 10 fix what is wrong before anything new is added.** Both
  Critical findings, and every High finding apart from H6 and H7, live there.
- **Phase 11 turns each fixed defect into a CI rule** so it cannot come back.
- **Phase 12 builds the evals that can show a plugin helps.** It needs the
  repaired harness from 8 and the stable behaviour from 9.
- **Phases 13 and 14 change content and add components.** They are measured
  with the Phase 12 evals.
- **Phase 15 writes down the rules the earlier phases made enforceable.**

**No new plugin in this iteration.** AUDIT §5 argues it course by course.
Summarised:
- every course that yields executable work fits an existing plugin;
- the seven already cost ~2,921 always-on tokens;
- the seven collide on triggers (M10);
- in 8 of 10 valid positive eval cases the plugin did not beat the no-plugin
  baseline (AUDIT §1.5).

---

## Phase 8 — Measurement that can fail

### 8.1 Fixture tests leave nothing behind *(H1)*

- **Change.**
  - `plugins/context-discipline/tests/run.sh:114-119` passes the throwaway
    repository as `cwd` in its fail-open probes.
  - Every `run.sh` runs its scripts with `cwd` set to a temporary directory
    and exports `PYTHONDONTWRITEBYTECODE=1`. Without it,
    `api-patterns/tests/run.sh` writes `scripts/__pycache__/` into the
    repository.
  - `validate.yml` runs the check below on a fresh clone.
- **Backing.** This is a repository defect, not a course concept. It is the
  root cause of the stale snapshot this audit's session received.
- **Done when.** A fresh clone stays byte-for-byte clean, including ignored
  files. The clone matters: an old `.claude/state/session.md` in a working
  copy would hide a test that rewrites it.

  ```bash
  d=$(mktemp -d) && git clone -q . "$d" && cd "$d"
  for t in plugins/*/tests/run.sh; do (cd "$(mktemp -d)" && bash "$d/$t" >/dev/null) || exit 1; done
  [ -z "$(git status --porcelain --ignored)" ]   # exit 0
  ```

- **Covered by.** The new `validate.yml` step "fixture tests leave no files".

### 8.2 Repair the eval cases that cannot pass *(H6)*

- **Change.**
  - **Missing fixtures.** Convert `delivery-quality/evals/review-format` and
    `verify-not-fired` to `case.yaml`, each with a `scaffold.sh` that creates a
    small project, plus an uncommitted change for `review-format`.
  - **Wrong graders:**
    - `team-rollout/evals/not-fired`: add "score well when" criteria. It
      currently fails a correct Shift+Tab answer.
    - `team-rollout/evals/settings-too-wide`: settle the order on
      credential-first and change `settings-review/SKILL.md:66` to match (see 13.6).
    - `skill-forge/evals/audit-finds-faults`: replace the name/directory fault
      with a real load failure, such as a loose `SKILL.md` or unclosed
      frontmatter (AUDIT M2).
  - **Case metadata.** Tag every case whose `allowed_tools` include Bash as
    `needs-bash`. Set `runs: 3` on positive cases.
- **Backing.** `introduction-to-claude-cowork.md:168-177` (compare with and
  without the skill, one change at a time).
  `claude-with-the-anthropic-api.md:188` (define grading criteria before
  implementing) and `:197` (the grader states strengths, weaknesses and
  reasoning).
- **Done when.**
  - `python3 .github/scripts/check_eval_cases.py` exits 0. This is a new
    script. It fails on a `prompt.md` case, on a grader without both "Score
    well" and "Score badly" sections, and on a Bash-using case without
    `needs-bash`.
  - A full `claude plugin eval` pass produces JSON in which no run has an
    `error` field.
- **Covered by.** `check_eval_cases.py` with its own fixtures in
  `.github/scripts/tests/`.

### 8.3 A local eval runner that says what it skipped *(AUDIT §1.5)*

- **Change.** `scripts/run-evals.sh`:
  - Runs every plugin with `--no-publish --output-dir` outside the repository.
  - Detects the condition that blocks Bash-granting runs (a symbolic link
    inside the Docker credential store).
  - In that case, runs with `--allow-tools Write Edit`, skips `needs-bash`
    cases, and prints them as *not run*.
  - It never alters the credential store.
- **Backing.** CONTRIBUTING.md's eval section.
- **Done when.** `bash scripts/tests/run-evals.test.sh` exits 0. The test sets
  `HOME` to a fixture with a linked `.docker/contexts` and asserts that the
  output lists the skipped cases, and that no case is scored while it lacks the
  tools it declares.
- **Covered by.** That test.

---

## Phase 9 — Safety defects

### 9.1 Scope `allowed-tools` *(C1)*

- **Change.**
  - Every skill that runs a script scopes the grant to that script:
    `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py *)`.
  - Advisory and review skills drop `Write` and `Edit`: `settings-review`,
    `claude-md-doctor`, `plan-rollout` and the java-spring and mcp-builder
    guidance skills.
  - Scaffolding skills keep `Write`/`Edit`, because creating files is their
    job: `write-a-skill`, `mcp-server-scaffold`, `eval-harness`. They list the
    reason in a `# allowed-tools:` line of the body.
  - `write-a-skill/SKILL.md:44` states that the field pre-approves tools.
  - `audit_skills.py` parses the frontmatter in every accepted form
    (comma-separated, space-separated, flow list, YAML list). It raises an
    error for a bare `Bash`, and a warning for `Write`/`Edit` on a skill with no
    stated reason.
- **Backing.**
  - `introduction-to-subagents.md:77-82`: minimal tools; a reviewer gets no
    edit tools.
  - `introduction-to-agent-skills.md:77`: `allowed-tools` for read-only flows.
  - Claude Code docs, *Pre-approve tools for a skill*.
- **Done when.**
  - `python3 plugins/skill-forge/scripts/audit_skills.py plugins/*/skills --json`
    contains no `bare-bash` error and no unjustified `write-grant` warning.
  - `audit_skills.py plugins/skill-forge/tests/fixtures/broken` reports new
    planted fixtures, one per accepted form: `allowed-tools: Bash Read`,
    `[Read, Bash]` and a YAML list.
- **Covered by.** A skill-forge fixture plus the CI audit step (11.1).

### 9.2 Rebuild `guard_destructive` matching *(C2, M6)*

- **Change.**
  - Split the command into segments on `;`, `&&`, `||` and `|`, and tokenise
    each with `shlex`.
  - Ignore heredoc bodies and quoted arguments for the `rm` and `git` rules
    only. SQL arrives inside quotes (`psql -c "…"`), so the SQL rules keep
    scanning quoted text.
  - Accept flags in any position, `-R`, and `+refspec`. Treat `$VAR` or
    backtick targets as outside the project.
  - Count tracked changes only (`--untracked-files=no`), and allow
    `git clean -n`.
  - Replace the messages with the model-directed versions in the
    tool-schema-review report: no "run it yourself", and no
    `--force-with-lease` to the protected branch.
- **Backing.** `claude-code-in-action.md:99-101` (PreToolUse is the enforcement
  primitive), `:122-126` (exit codes). `claude-code-101.md:170` (block
  `rm -rf` and commits to main).
- **Done when.** `plugins/delivery-quality/tests/run.sh` passes with at least
  15 new fixtures, and the audit's probe cases all return 2:
  - flag-first `--force`, `-f` and `+main` pushes;
  - `-Rf`, flags after the target, and `$HOME` targets;
  - `DROP` with `2>/dev/null`;
  - `kubectl delete pods --all`;
  - `psql -c "DELETE FROM users" -d prod`.

  Three false positives return 0: a heredoc containing `rm` text, `reset
  --hard` with only untracked files, and `git clean -n`.
- **Covered by.** Those fixtures.

### 9.3 Close `guard_secrets` *(C2, M6, M15)*

- **Change.**
  - Scan `new_source` (NotebookEdit).
  - Put `.claude/*-guard-allow` in `BLOCKED_PATHS`. The message asks the user,
    not the model, to add an exception.
  - Read `tool_name`: a Bash command is scanned only where it writes (a
    redirect, `tee`, a heredoc to a file). A search for a key pattern passes.
  - Exempt `.env.example|sample|template`, whose content is still scanned.
  - Anchor the matcher and add `PowerShell`.
- **Backing.** `claude-code-in-action.md:128` (guard what reaches disk).
  CONTRIBUTING.md "Writing a hook" (a fixture for every branch that blocks or
  must pass).
- **Done when.** `run.sh` passes with new fixtures:
  - blocked: a NotebookEdit carrying a key, and a write to the allow file;
  - passes: `grep -rnE 'AKIA[0-9A-Z]{16}' src/`, and `.env.example` with
    `${PLACEHOLDER}` values.
- **Covered by.** Those fixtures.

### 9.4 Make `restore_state` truthful and local *(H1, H2, M7, M14)*

- **Change.**
  - **Registration.** Delete the PostCompact entry. Give SessionStart the
    matcher `compact`, and optionally `resume` after an eval shows it helps.
  - **What gets restored.** Restore only a snapshot written by the same
    session, or its predecessor on compaction. Never fall back to another
    file.
  - **Where snapshots live.** Store them under `${CLAUDE_PLUGIN_DATA}`, keyed
    by the repository's top-level path, not inside the repository. A cloned
    repository's `.claude/state/` then becomes inert.
  - **Header.** Say which `source` fired. Label the handoff note as written by
    the assistant, with its date.
  - **Handoff.** Read `.claude/handoff.md` live when it is newer than the
    snapshot.
  - **Size.** Cap the output at 8,000 characters, with branch and handoff
    first.
  - **Honesty.** Report "not a git repository" instead of "clean" when git
    fails. Fix "compaction compaction".
- **Backing.** `claude-code-in-action.md:108`, `:130`, `:245`, `:248-253`
  (re-inject with SessionStart on `compact`, not PostCompact).
  `ai-capabilities-and-limitations.md:144` (instructions embedded in content
  get followed). Hooks docs: decision-control table and the 10,000-character
  cap.
- **Done when.**
  - `grep -c PostCompact plugins/context-discipline/hooks/hooks.json` returns `0`.
  - `run.sh` passes new cases:
    - a `startup` payload next to a foreign snapshot prints nothing;
    - a `compact` payload restores its own snapshot;
    - a clone carrying `.claude/state/x.md` prints nothing;
    - an oversized tree yields output of at most 8,000 characters that
      contains the handoff line;
    - a non-git directory never prints "clean".
- **Covered by.** Those fixtures, plus a new eval case: compaction mid-task,
  then "what was I doing?".

### 9.5 Remove the command that shadows a skill *(H3)*

- **Change.** Delete `skill-forge/commands/audit-skills.md`. Its defaults
  (check `.claude/skills` and `~/.claude/skills`) move into the skill body. The
  skill stays invocable as `/skill-forge:audit-skills`.
- **Backing.** `introduction-to-agent-skills.md:57-63`, `:128` (same-name
  priority silently hides one component). Observed behaviour in AUDIT H3.
- **Done when.** `claude plugin details skill-forge@pacoromerodev` lists
  `audit-skills` once. With Bash available, the `audit-finds-faults` eval shows
  the audit script running (a `tool_used: Bash` grader).
- **Covered by.** The eval grader, and the collision check in 11.2.

### 9.6 Make the test gate honest about what it checked *(M5, M14, M15)*

- **Change.**
  - Parse `CLAUDE_TEST_GATE_TIMEOUT` inside `main()`.
  - Clamp the effective timeout below the hook's own.
  - `only_when_changed` also diffs against the commit the session started from.
  - Drop the `stop_hook_active` short-circuit and rely on Claude Code's own cap
    on consecutive blocks, or re-run the tests.
  - Report failures as Stop `additionalContext`, capped at 4,000 characters,
    with the first failing line at most 300 characters.
  - An opted-in gate that cannot run says so through `systemMessage`.
  - The README matches the code.
- **Backing.** `claude-code-in-action.md:94`, `:190` (a Stop hook running tests
  is the correctness gate), `:126` (exit 2 on Stop).
- **Done when.** `run.sh` passes new cases:
  - `CLAUDE_TEST_GATE_TIMEOUT=15m` → exit 0 with the default applied;
  - `{"timeout": 1800}` → effective at most 940;
  - a committed change under `only_when_changed` → the gate runs;
  - a 300,000-character failure line → output at most 4,000 characters;
  - an opted-in gate with no runner → a `systemMessage` is present.
- **Covered by.** Those fixtures, run in a temporary git repository.

### 9.7 Resolve the project root from the payload *(M13)*

- **Change.** All five scripts take the root from the payload `cwd`, resolved
  with `git rev-parse --show-toplevel`. `CLAUDE_PROJECT_DIR` is used only to
  find the allow files.
- **Backing.** Hooks docs: `cwd` follows Claude into worktrees;
  `CLAUDE_PROJECT_DIR` stays where the session started.
- **Done when.** A `run.sh` case creates a `git worktree` with a failing,
  uncommitted change, next to a clean main checkout, with
  `CLAUDE_PROJECT_DIR` pointing at the main checkout. For the worktree
  payload:
  - `test_gate` exits non-zero;
  - `guard_destructive` blocks `git reset --hard`;
  - `save_state` records the worktree's branch.
- **Covered by.** That fixture.

---

## Phase 10 — Settings that do what they claim *(H4, H5)*

- **Change.**
  - **Managed template.** `strictKnownMarketplaces` becomes an array holding
    one placeholder source, paired with `extraKnownMarketplaces` to register it.
    Delete `knownMarketplaces`.
  - **Project template.** Move `$comment` out of `hooks`.
  - **Checker.** `check_settings.py` checks the type of
    `strictKnownMarketplaces`, where an empty list means lockdown and is
    reported as such. It flags `knownMarketplaces` as unknown, and warns on
    `github` or `git` sources in `extraKnownMarketplaces` that have no `ref`.
  - **Fixtures.** `good-settings.json` is made valid. A new
    `bad-marketplace-bool.json` carries the boolean form. `bad-settings.json`
    keeps exercising `open-marketplaces`, so it is left alone.
  - **CI.** A new CI script validates the templates and fixtures against a
    pinned copy of the schemastore schema. CI scripts may use `jsonschema`: the
    stdlib rule covers `plugins/*/scripts` only, and this item says so in
    CONTRIBUTING.md.
- **Backing.** `introduction-to-agent-skills.md:104-111`, `:145`
  (`strictKnownMarketplaces` is an allowlist array in managed settings).
  `deploying-claude-enterprise-with-confidence.md:113` (the platform owner ships
  managed settings). `claude-code-in-action.md:198-200` (private marketplace;
  read before installing).
- **Done when.**
  - `python3 .github/scripts/validate_settings_schema.py` reports 0 errors.
  - `check_settings.py tests/fixtures/bad-marketplace-bool.json --managed`
    reports the boolean `strictKnownMarketplaces`.
  - A new fixture with an unpinned `github` marketplace produces the "unpinned"
    warning.
  - Configured from `settings/`, `claude plugin marketplace add <unlisted repo>`
    is refused on a test machine. That last check is manual; see *Not
    automatable* below.
- **Covered by.** team-rollout fixtures and the schema CI step.

---

## Phase 11 — CI gates for everything Phases 8–10 fixed

Each new script gets its own fixtures under `.github/scripts/tests/`, run by a
`validate.yml` step. That step is the "covered by" for every row.

| # | Gate | Backing | Done when |
|---|---|---|---|
| 11.1 | `audit_skills.py plugins/*/skills` in `validate.yml` | `introduction-to-agent-skills.md:124`, `:145` (validator in CI before publishing) | A branch that adds a bare `Bash` grant fails CI |
| 11.2 | `check_names.py`: a command and a skill sharing a name inside one plugin is an error. A command and an agent sharing a name (today `mcp-builder`'s `mcp-review`), and any name repeated across plugins, are warnings. `audit_skills.py` also compares agent and command descriptions, not only `SKILL.md` | `introduction-to-agent-skills.md:57-63`, `:127` | A fixture plugin with a colliding command and skill makes it exit 1; `main` exits 0 with the `mcp-review` warning listed |
| 11.3 | `check_eval_coverage.py`: two positive cases (tagged with the skill name) and one negative per skill; one positive per agent. Report-only until Phase 12 closes, then enforced | CONTRIBUTING.md:94-97; `introduction-to-claude-cowork.md:186-190` (evals before each publication) | `--enforce` exits 0 on `main` |
| 11.4 | `check_course_wording.py`: 8-word shingles of `plugins/**` text against the English code blocks in the academy notes, from a pinned checkout of the public academy repo | Go-public item 3 | Flags `rag-retriever/SKILL.md:88-91` before 13.2 and nothing after. It cannot see a paraphrase of Spanish prose; see the clash table |
| 11.5 | `evals.yml`: `permissions: contents: read`, `persist-credentials: false`, inputs through `env:`, Claude Code pinned (same in `validate.yml`), and the `ANTHROPIC_API_KEY` secret actually set. The weekly schedule runs every plugin at `runs: 1`; the `runs: 3` pass of Phase 12 is manual, before a release | `claude-code-in-action.md:166-183` (Action with minimal tools and a turn cap) | Both workflow files contain `permissions:` and `persist-credentials: false`; no `run:` block contains `${{`; the next scheduled run gets past the secret check. 14.2 re-asserts this later |
| 11.6 | Supported Python stated once. Either 3.8 stays (drop `tomllib` from the allowed set and pin `ubuntu-24.04` for that leg) or the floor moves to 3.10 | AUDIT M12 | The CI matrix and `check_stdlib_only.py` agree; a fixture importing `tomllib` fails on the 3.8 leg |
| 11.7 | `hooks.json` commands use `${CLAUDE_PLUGIN_ROOT}` and point at scripts that exist | CONTRIBUTING.md:64-65 | A fixture `hooks.json` with a relative path fails |
| 11.8 | `check_consistency.py` reports a plugin directory with no `plugin.json` instead of skipping it (AUDIT L5) | CONTRIBUTING.md "Adding a plugin" | A fixture directory with no manifest makes it exit 1 |

**Also done when:** a deliberately broken branch is pushed as a pull request
and fails. This is the ROADMAP 0.1 criterion that was never evidenced
(AUDIT M9), and the PR link goes in this file.

**Evidenced:** pacoromerodev/claude-code-toolkit#6 planted a bare `Bash` grant
and a relative hook path. Run 35723853440 failed on both — the skill auditor
and `check_hooks.py` — and on a third fault nobody planted: shellcheck's
SC1007 in `scripts/tests/run-evals.test.sh`, which had been failing the Shell
scripts job on every pull request of this stack since Phase 8. Fixed at the
base, the stack rebased, and #6 closed.

---

## Phase 12 — Evals that can show a plugin helps *(H6)*

- **Change.**
  - Every skill gets two positive cases and one negative; every agent gets one
    positive.
  - A candidate positive prompt is **piloted against the baseline first**, and
    kept only if the plugin arm beats it in at least 2 of 3 runs. A case the
    baseline passes measures nothing. Eight of today's ten valid positive
    cases are like that; they are re-worded or replaced, not deleted.
  - Negative cases keep the shape they have.
- **Backing.** `introduction-to-claude-cowork.md:172-177` (with and without,
  and "clearly better than baseline" is the bar).
  `claude-with-the-anthropic-api.md:139-148` (a single try misses edge cases).
- **Done when.**
  - `check_eval_coverage.py --enforce` exits 0.
  - For each plugin, `claude plugin eval` with `runs: 3` reports
    `overallScore ≥ 0.8` and `meanDelta > 0` in its JSON.
  - A plugin that cannot reach `meanDelta > 0` after Phase 13 is proposed for
    removal in this file, rather than having its graders loosened.
- **Covered by.** The eval suites themselves. The weekly CI matrix (11.5) keeps
  them honest.
- **Cost.** Extrapolated from this audit's $6.98 for 22 cases × 1 run × 2 arms:
  roughly 60 cases × 3 runs × 2 arms comes to about $55–60 per full pass, plus
  the pilot runs. That is why the weekly CI run stays at `runs: 1` (about
  $20 a week at 60 cases). Budget both before starting.

### What the pilot showed

Run on 2026-09-22 and 23 against the working copy, `runs: 3`, both arms, at a
cost of about $18. Every case tagged `needs-bash` is missing from these
numbers, for the reason under *Not done here* — including seven of
delivery-quality's eight, which is its whole measurable surface.

| Plugin | Case | With | Baseline | Δ |
|---|---|---|---|---|
| api-patterns | `agent-that-must-resume` | 0.67 | 0.33 | +0.33 |
| api-patterns | `bedrock-model-not-found` | 1.00 | 0.67 | +0.33 |
| api-patterns | `cache-ttl-mismatch` | 1.00 | 1.00 | +0.00 |
| api-patterns | `chunks-lose-their-heading` | 1.00 | 1.00 | +0.00 |
| api-patterns | `hybrid-or-rerank` | 1.00 | 1.00 | +0.00 |
| api-patterns | `not-fired` | 1.00 | 1.00 | +0.00 |
| api-patterns | `score-jumped-after-examples` | 1.00 | 1.00 | +0.00 |
| api-patterns | `tool-never-chosen` | 1.00 | 1.00 | +0.00 |
| api-patterns | `workflow-not-agent` | 1.00 | 1.00 | +0.00 |
| context-discipline | `context-cannot-be-measured` | 0.67 | 0.00 | +0.67 |
| context-discipline | `fix-before-scope` | — | — | not re-measured after its repair |
| context-discipline | `not-fired` | 1.00 | 1.00 | +0.00 |
| context-discipline | `rules-nobody-follows` | 1.00 | 1.00 | +0.00 |
| delivery-quality | `verify-not-fired` | 1.00 | 1.00 | +0.00 |
| java-spring | `config-in-service` | 1.00 | 1.00 | +0.00 |
| java-spring | `flaky-time-test` | 1.00 | 1.00 | +0.00 |
| java-spring | `legacy-date-parsing` | 1.00 | 1.00 | +0.00 |
| java-spring | `not-fired` | 1.00 | 1.00 | +0.00 |
| java-spring | `out-of-order-updates` | 1.00 | 1.00 | +0.00 |
| java-spring | `records-or-lombok` | 1.00 | 1.00 | +0.00 |
| java-spring | `transaction-boundary` | 1.00 | 1.00 | +0.00 |
| java-spring | `what-to-test` | 1.00 | 1.00 | +0.00 |
| mcp-builder | `not-fired` | 1.00 | 1.00 | +0.00 |
| mcp-builder | `roots-are-advice` | 1.00 | 1.00 | +0.00 |
| mcp-builder | `server-from-an-api` | — | — | not re-measured after its repair |
| mcp-builder | `stdio-or-http` | 1.00 | 1.00 | +0.00 |
| mcp-builder | `tool-or-resource` | 1.00 | 1.00 | +0.00 |
| skill-forge | `description-rewrite` | 0.00 | 0.67 | -0.67 |
| skill-forge | `not-fired` | 1.00 | 1.00 | +0.00 |
| skill-forge | `procedure-into-skill` | — | — | not re-measured after its repair |
| skill-forge | `skill-or-subagent` | 0.67 | 0.67 | +0.00 |
| team-rollout | `connector-with-write` | 1.00 | 0.00 | +1.00 |
| team-rollout | `local-settings-committed` | 1.00 | 1.00 | +0.00 |
| team-rollout | `not-fired` | 1.00 | 1.00 | +0.00 |
| team-rollout | `rollout-order` | 1.00 | 0.00 | +1.00 |

32 cases measured both ways; mean score 0.94, mean delta +0.08. 18 of the suite's 53 cases need Bash and did not run.

**The baseline answers most of these prompts correctly.** That is the finding,
and it is the same one AUDIT §1.5 reported at `runs: 1`: on a conceptual
question — where `@Transactional` goes, whether to use a record, why a
reranker cannot recover a document that was never retrieved — the model
without any plugin gives an answer that satisfies a grader written from the
skill's own content. A skill that repeats what the model already knows costs
context and returns nothing.

Delta comes from four kinds of case, and only those:

1. **Facts the model cannot have current.** `bedrock-model-not-found`
   (+0.33): the error says the model does not exist, and the answer is a
   cross-region inference profile.
2. **Facts about the model's own situation.** `context-cannot-be-measured`
   (+0.67): without the plugin it invents a percentage, which is what the user
   asked for and the one thing it cannot know.
3. **An order or a framing the model does not reach on its own.**
   `rollout-order` (+1.00) and `connector-with-write` (+1.00): spend answered
   before identity, and a write-capable connector treated as a switch rather
   than as three gates and a signature. Both score 0.00 without the plugin.
4. **A decision the content added in Phase 13.**
   `agent-that-must-resume` (+0.33), after its repair.

Everything else — nineteen cases — is 1.00 against 1.00.

One case still scores **below** the baseline: `description-rewrite`, at 0.00
against 0.67. It is not an environment artefact. With skill-forge loaded, the
main thread rewrites the description itself instead of delegating to
`skill-describer`, and returns one candidate where the grader wants several
compared. That is a finding about the subagent, not about the case: a
subagent nothing delegates to is context spent on a description nobody acts
on. It stays as it is, unfixed, because the fix is a decision about the
component — sharpen the boundary or drop the subagent — and that belongs in a
later phase, not in a grader.

Four cases were repaired rather than kept, because the pilot showed they
measured nothing. Two of the four — `fix-before-scope` and
`server-from-an-api` — ran in an empty sandbox, so the case described a
repository that was not there; the plugin arm went looking for it and the
baseline simply answered. Both now scaffold what the prompt describes. Neither
has been re-measured: the re-runs died on a usage limit and on a turn limit
that has since been raised.

- `procedure-into-skill` asked for a skill where a command is the right
  answer: cutting a release is user-initiated. Both arms proposed a command
  and the grader called that wrong. It now describes a correction that recurs
  on its own.
- `agent-that-must-resume` failed both arms. The plugin's answers were correct
  engineering — persist a record of progress — and the grader demanded the
  skill's own phrasing instead. The grader now requires the part the skill
  adds (who runs the loop) and accepts a checkpointed self-run loop; the
  skill's description gained the trigger it was missing, which is why it had
  not fired.

Per plugin, over the cases that ran:

| Plugin | Cases | Mean score | Mean Δ |
|---|---|---|---|
| team-rollout | 4 | 1.00 | +0.50 |
| context-discipline | 3 | 0.89 | +0.22 |
| api-patterns | 9 | 0.96 | +0.07 |
| delivery-quality | 1 | 1.00 | +0.00 |
| java-spring | 8 | 1.00 | **+0.00** |
| mcp-builder | 4 | 1.00 | **+0.00** |
| skill-forge | 3 | 0.56 | **−0.22** |

**What this means for the plugins.** The bar this plan set was
`overallScore ≥ 0.8` and `meanDelta > 0`. Three plugins clear it;
delivery-quality has one measurable case and is not judged on it. Three do
not, and the rule was that they are proposed for removal here rather than
re-graded:

- **java-spring** — eight cases, delta exactly zero. The proposal is below.
- **mcp-builder** — four cases, delta zero, with two of its five repaired or
  unmeasured. It needs the `needs-bash` cases and a re-run of
  `server-from-an-api` before anything is decided; those three cases are its
  checker and its transport losses, which is where a delta would be.
- **skill-forge** — the only negative mean, and it comes from one case where
  the plugin makes the answer worse by not delegating. Its other two
  measurable cases are unrepaired or tied. The same re-run applies.

The honest reading of the whole table is narrower than "the plugins help": a
current fact helps, an order of decisions helps, a checker probably helps, and
conceptual prose that restates what the model already knows does not. The
plugins whose value is a checker — `check_api_calls.py`, `check_settings.py`,
`check_mcp_server.py`, the guards — are exactly the ones whose cases need
Bash, and therefore the ones this machine could not measure at all.

### Proposed for removal: `java-spring`

The rule this plan set for Phase 12 is that a plugin which cannot reach
`meanDelta > 0` is proposed for removal here, rather than having its graders
loosened. `java-spring` is in that position, and this is the proposal.

**The measurement.** Eight cases ran, `runs: 3`, both arms. Every one scored
**1.00 with the plugin and 1.00 without it**: mean delta exactly 0.00. The
cases were not soft — they carry a wrong plan for the answer to push back on
(commit offsets earlier, raise the sleep, move `@Transactional` to the
controller, convert entities to records) — and the model refused every one of
them with no plugin loaded.

**What is not measured.** Two of its ten cases need Bash, so they did not run
here: `migration-unsafe` (the `migration-review` subagent, on a real
repository with a checked-in query the migration breaks) and
`kafka-redelivery`. The subagent is the component with the most plausible
remaining value: its output format, and the deploy order it returns, are not
things a plain answer produces. Neither has been shown to help.

**The three options, and the recommendation.**

1. **Remove the plugin.** Honest, and it loses the migration subagent along
   with everything else, unmeasured.
2. **Keep it and say what it is for.** Its README would have to say that on
   general Spring and Kafka questions the model does as well without it, and
   that what it adds is the review subagent's shape and the house rules a
   particular team wants enforced. That is a real use — a team's conventions
   are not in the model — but it is not what the plugin claims today.
3. **Reduce it to the parts that could still show a delta**: the
   `migration-review` subagent and the conventions that are genuinely local,
   dropping the skills that restate what the model knows. Four skills at ~449
   always-on tokens would become one subagent at a fraction of that.

**Recommended: (3), after the two Bash cases run.** Removing a plugin on
evidence that excludes its strongest component would be the same mistake this
audit was written to stop. The gate is CI with the `ANTHROPIC_API_KEY` secret
set, which runs the `needs-bash` cases this machine cannot. If
`migration-unsafe` also shows no delta, (1) follows.

`mcp-builder` and `skill-forge` are in the same position on the numbers, and
neither gets a proposal yet for the same reason: too much of each is
unmeasured. mcp-builder's three `needs-bash` cases are its checker and its
transport losses; skill-forge's are its auditor. Those are where a delta would
be if there is one, and they run in CI as soon as the secret exists.

The same question is open, less sharply, for the conceptual skills in every
plugin: see the deltas in the table above.

---

## Phase 13 — Content corrections

Each row changes plugin text to match its source and adds or updates the eval
or fixture that would catch the regression.

Unless a row says otherwise, "Done when" means the named case or fixture
passes: an eval case at the Phase 12 bar, or a fixture in the plugin's
`run.sh`.

| # | Change | Backing | Done when | Covered by |
|---|---|---|---|---|
| 13.1 | `eval-harness`: attribute the 3.9 → 7.9 jump to specific output guidelines; teach examples as the next step; add generating the dataset with a fast model and reusing top-scored outputs as examples | `claude-with-the-anthropic-api.md:163`, `:236`, `:245`, `:278`, `:806` | `grep -n "comes from examples" plugins/api-patterns/skills/eval-harness/SKILL.md` prints nothing, and the new case passes | Case: "my prompt went from 4 to 8 after I added examples — was it the examples?" (grader: asks what else changed) |
| 13.2 | `rag-retriever`: the contextual-retrieval template takes the document (or its opening chunks plus the preceding ones) and the chunk, reworded in the plugin's own words | `claude-in-amazon-bedrock.md:135-144` | The template has a document slot; `check_course_wording.py` (11.4) reports nothing for the file | Case: "retrieval misses chunks that only make sense with the section heading" |
| 13.3 | `choose-transport` and `mcp-roots-check`: add List Roots to what stateless mode loses and to the pre-switch grep; `json_response` also drops progress and logs; settle the logging-under-stateless claim against the SDK before keeping or dropping it | `model-context-protocol-advanced-topics.md:143`, `:146`, `:163`, `:165`, `:170-178` | The grep line in the skill contains `list_roots`; both cases pass | `stateless-tradeoff` grader updated; new case with a server that calls `list_roots()` |
| 13.4 | `prompt-cache-audit` and `check_caching.py`: automatic caching exists; the minimum is model-specific; TTL is 5 min by default with 1 h opt-in; drop or invert `cache-on-tail` | API docs (the note's concept at `claude-with-the-anthropic-api.md:593-624`; its numbers are out of date) | `grep -rn "never automatic" plugins/api-patterns` prints nothing; the fixtures pass | api-patterns fixtures: a top-level `cache_control` gets no automatic-caching hint; a breakpoint on the last message raises no warning |
| 13.5 | `write-a-skill` and `audit-skills`: a name/directory mismatch is a portability warning, not a load error; required fields per Claude Code; subagents can invoke skills, and `skills:` preloads; inline the component decision rules instead of pointing at `docs/anatomy.md`, which the plugin does not ship (L7) | `introduction-to-agent-skills.md:48`, `:67-73`, `:113-121` read against the Claude Code docs | `audit_skills.py` on the `name-mismatch` fixture exits 0 with a warning; on a fixture citing a file outside the plugin it exits 1 | skill-forge fixtures, including the existing `dead-reference` one |
| 13.6 | `settings-review`: never write `${CLAUDE_PLUGIN_ROOT}` as advice (M3); an invalid file raises a Settings Error dialog; report order is literal credential, then grants wider than intended, then what never runs | Claude Code settings docs; `claude-code-in-action.md:194-200` | In `settings-review/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}` appears only on the `python3 …` invocation lines | `settings-too-wide`, with the grader aligned in 8.2 |
| 13.7 | Trigger rewrites, starting from the `skill-describer` recommendations: `write-a-skill` hands "not firing" to the audit and the describer; `tool-schema-review` and `mcp-review` say where the tools live; `code-reviewer` drops "before a commit"; `test-shape` says Java and Spring | `introduction-to-agent-skills.md:125-127`; `introduction-to-subagents.md:60`, `:65-68` | `route_check.sh` exits 0: each fixed prompt invokes the component it belongs to | `scripts/route_check.sh` (new): with all seven plugins enabled, run fixed prompts through `claude -p --output-format stream-json` and assert which Skill or Agent was invoked. `plugin eval` loads one plugin at a time, so it cannot measure a collision between two |
| 13.8 | `claude-md-doctor` and `check_claude_md.py`: a rule that must never be broken belongs in a PreToolUse hook; start without a CLAUDE.md and add a rule only for a correction that repeats; put critical rules first and repeat them last | `claude-code-in-action.md:36`, `:53`; `claude-code-101.md:114`; `ai-capabilities-and-limitations.md:126-132` | Both new fixtures produce their finding; `good-CLAUDE.md` stays clean | Fixture: a "NEVER push to main" rule produces a hook suggestion; a long file with its only emphasised rule in the middle produces a placement warning |
| 13.9 | `plan-rollout`: add the connectors decision (three gates, read before write, sign-off by the risk owner), the deployment objective, decision owners, and the spend levers that are not limits. Reword the fictional-company example in the plugin's own terms | `deploying-claude-enterprise-with-confidence.md:30`, `:35-48`, `:129-148`, `:186`, `:198-202` | The new case passes | Case: "give the payments team the Drive connector with write access" (grader: separate group, the three gates, write sign-off) |
| 13.10 | `agent-or-workflow`: when it is an agent, choose between your own loop, the tool runner and managed agents | `claude-platform-101.md:99`, `:119-130`, `:316-317` | The new case passes | Case: "long-running file clean-up agent, resumable after a network failure" |
| 13.11 | `/context`: say plainly that the model cannot measure the context, and send the user to the built-in `/context` for the numbers | `claude-code-101.md:88` | The new case passes | A case whose grader requires both statements |
| 13.12 | Remove the command files that only say "use skill X" (L3), keeping the skill invocable by `/plugin:skill`. Commands that launch a subagent stay | AUDIT §1.2 | The total from `claude plugin details` over the seven plugins falls below 2,921 always-on tokens, and Phase 12 scores do not drop | `claude plugin details` output recorded in the PR |
| 13.13 | README: list `guard_destructive` (L2); drop "private" (L6); correct the test-gate timeout sentence (M5) | Go-public item 5 | `grep -c guard_destructive README.md` ≥ 1; `grep -ci private README.md` = 0; the README timeout sentence matches the exit code in `test_gate.py` | The README review in the go-public checklist |
| 13.14 | `verify-changes` and `code-reviewer`: include untracked files in scope (`git status --porcelain` plus `git ls-files --others --exclude-standard`, read in full), and take the test command from the project's `.claude/test-gate.*` when present, before the runner table (M16) | `claude-code-in-action.md:55-64` (tests, then the diff, then weakened tests, with evidence) | Both new cases pass | Two cases: a change made only of new files, one of them a test asserting nothing, which `verify-changes` must flag; and a repository whose tests are declared in `.claude/test-gate.json`, which it must run |

---

## Phase 14 — Components from the coverage audit

| # | Component | Plugin | Backing | Done when / covered by |
|---|---|---|---|---|
| 14.1 | **Agent auditor.** `audit_skills.py` also reads `agents/*.md`. It flags edit tools on a reviewer, an output format without an "Obstacles" section, a description that says neither when to delegate nor what to pass, and an "expert" persona line | skill-forge | `introduction-to-subagents.md:60`, `:65-68`, `:70-82`, `:96-97` | New broken-agent fixtures reported. The five shipped agents pass. Case: "my review subagent rambles and never finishes" |
| 14.2 | **Unattended-run checker.** `check_workflows.py` plus a section in `verify-changes`. For GitHub workflows that run Claude, it flags: no `permissions:`, checkout keeping credentials, `${{ inputs.* }}` or `${{ github.event.* }}` inside `run:`, unpinned CLI or action, no `--max-turns`, broad tools, bypass permission mode | delivery-quality | `claude-code-in-action.md:155-192`; `claude-in-amazon-bedrock.md:157-169` | A fixture copy of today's `evals.yml` yields each M4 finding; the hardened workflow (11.5) is clean |
| 14.3 | **Redact instead of block** (opt-in). `guard_secrets` rewrites the Bash call through `updatedInput`, replacing the secret with a placeholder, and returns the full input object | delivery-quality | `claude-code-in-action.md:110-120`, `:128` | Fixture: a command containing a key gives exit 0 and JSON with `permissionDecision` and the complete `updatedInput`, key absent |
| 14.4 | **API-call checker.** `check_caching.py` grows into `check_api_calls.py`. It adds thinking combined with `temperature` or prefill, a thinking budget under 1,024 or not below `max_tokens`, `effort` outside `output_config`, `system=None`, and a tool loop that does not return `is_error` results | api-patterns | `claude-with-the-anthropic-api.md:74`, `:381`, `:527`, `:543`; `claude-platform-101.md:136` | One bad and one good fixture per rule in `tests/` |
| 14.5 | **Providers reference.** `references/providers.md` covers Bedrock (`converse`, `toolChoice`, `toolResult.status`, inference profiles) and Vertex (Model Garden, application-default credentials, `AnthropicVertex`). `eval-harness` and `tool-schema-review` link to it | api-patterns | `claude-in-amazon-bedrock.md:23-73`; `claude-with-google-vertex.md:12-23`; ROADMAP.md:193 | Case: "Bedrock says the model does not exist in my region" (grader: inference profile) |
| 14.6 | **Builder lenses.** `verify-changes` checks that any package the change introduces resolves, against the lockfile or registry. `code-reviewer` checks the change against stated acceptance criteria when they exist | delivery-quality | `ai-fluency-for-builders.md:40`, `:56`, `:83-90` | Case: a scaffold that adds a non-existent package, and `verify-changes` must flag it. Case: a change whose tests pass but miss a stated criterion |

---

## Phase 15 — A CLAUDE.md for this repository

- **Change.** Add a short `CLAUDE.md`. The draft below was written during the
  audit and passed `check_claude_md.py` (`Clean — 26 lines, nothing to
  report.`). Every rule maps to a command.
- **Backing.** `claude-code-in-action.md:33-53` (short, specific, checkable,
  alternative named). `claude-code-101.md:114` (add rules for corrections that
  actually recur; this audit is that record).
- **Depends on.** 9.1 (the `allowed-tools` rule), 8.1 (tests run from a temp
  directory), 11 (the commands exist in CI).
- **Done when.**
  - `python3 plugins/context-discipline/scripts/check_claude_md.py CLAUDE.md`
    exits 0.
  - Every command block in it exits 0 on `main`.
- **Covered by.** A `validate.yml` step running the checker on `CLAUDE.md`.

The draft:

````markdown
# claude-code-toolkit

A marketplace of Claude Code plugins under `plugins/`. Review criteria live in
`CONTRIBUTING.md`; this file holds only the rules that each map to a command.

## Before you commit

Run these from the repository root; each must exit 0:

```bash
claude plugin validate . && for d in plugins/*/; do claude plugin validate "$d"; done
python3 .github/scripts/check_consistency.py
python3 .github/scripts/check_stdlib_only.py
python3 plugins/skill-forge/scripts/audit_skills.py plugins/*/skills
rc=0; for t in plugins/*/tests/run.sh; do (cd "$(mktemp -d)" && bash "$OLDPWD/$t") || rc=1; done; [ "$rc" -eq 0 ]
```

Run the fixture tests from a temporary directory, as above: some hook tests
write session files into the current directory.

## Rules

- Hook scripts import only the standard library; `check_stdlib_only.py` enforces it.
- A new block or allow branch in a hook ships with a fixture in `tests/fixtures/`
  for the blocked input and one for the input that must pass.
- A version bump changes `plugin.json`, the `marketplace.json` entry and the
  plugin's `CHANGELOG.md` in the same commit.
- In `allowed-tools`, scope `Bash` to the script the skill runs, for example
  `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_x.py *)`; write `Bash` alone only
  with a reason in the commit message.
- Paraphrase course material in English and cite `web/src/<course>.md:<line>`;
  paste no sentence from the notes.
- Keep `.claude/state/` and `.claude/handoff.md` out of commits; `.gitignore` covers both.
````

Once 8.1 lands, the temp-directory sentence can go.

---

## Corrections to ROADMAP.md

ROADMAP.md is left as written; these are its known errors (AUDIT M9).

- `:115` — The "Correction" is itself wrong. PostCompact cannot inject context;
  SessionStart with `compact` can. Phase 9.4 fixes the hooks.
- `:188` — The cache TTL is 5 minutes by default; one hour is opt-in.
- `:187`, `:193` — `eval-harness` has no runner, and the Bedrock and Vertex
  references were never written. Phase 14.5 writes them.
- `:207-208` — `docs/rollout.md` and `docs/plugin-trust.md` do not exist. They
  are not re-planned as documents: `plan-rollout` (13.9) and the plugin-trust
  rules in `settings-review` (Phase 10) carry that content where it executes.
- `:40`, `:60`, `:210` — These done-criteria were not met. Phases 11, 12 and
  10 re-establish them with commands.

---

## Clashes with "Before making this repository public"

| Checklist item | Clash | Resolution in this plan |
|---|---|---|
| 1. Grep history for employer terms | The audit adds two files to history. They contain no absolute home-directory paths or local usernames (checked by grep before the commit). They do name the owner's public GitHub handle, already public in `marketplace.json`, and a local branch | Accept. Neither is an employer term. Run the item-1 grep after this commit anyway |
| 3. No Academy text verbatim | `rag-retriever/SKILL.md:88-91` is close to an English course prompt. `plan-rollout/SKILL.md:144-147` follows the note's fictional-company example | 11.4 catches the first. It cannot catch the second, a paraphrase of Spanish prose, so that one stays a **manual read** in the checklist. 13.2 and 13.9 reword both. **Publication is blocked until 11.4 is clean and the manual read is done** |
| 4. Validate and evals green on a clean clone | Impossible today: two cases cannot pass, and Bash-needing cases cannot run on a machine like the audit's (H6, AUDIT §1.5) | Phases 8 and 12. Define "green" as the Phase 12 bar (`overallScore ≥ 0.8`, `meanDelta > 0`, `runs: 3`). A plugin that cannot meet it is removed, not re-graded |
| 5. README someone else can follow | README.md:12 says the repository is private, and the delivery-quality table is incomplete | 13.13 |
| (new) Eval reports | `claude plugin eval` publishes its HTML report to claude.ai by default, with local paths in it | Keep `--no-publish` in CI and in `scripts/run-evals.sh` (8.3) |
| (new) The security findings themselves | Publishing AUDIT.md documents working guard bypasses (C2) and an injection path (H1) | Ship Phase 9 before, or together with, making the repository public |

---

## Excluded — not verifiable, or not worth a component

- **Skills for `/goal`, worktrees or routines.** These are built-in Claude Code
  features (`claude-code-in-action.md:26-29`, `:132-153`). A skill would only
  restate the docs, and no check could fail. The verifiable part of unattended
  runs is 14.2.
- **Computer use** (`claude-in-amazon-bedrock.md:171-182`). It needs a sandboxed
  desktop, and nothing in a repository can be checked.
- **A client-side MCP skill**
  (`introduction-to-model-context-protocol.md:86-167`). Client code is
  application-specific, with no fixture shape that generalises.
- **Any AI-usage-policy generator** from the eight AI Fluency courses. The
  output is a human deliberation document; a generator produces the generic
  text those courses warn against, and no grader could tell a good policy from
  a plausible one.
- **"Improve the wording" of skills** with no routing check or eval. 13.7 is
  the verifiable form.
- **A second iteration of `docs/anatomy.md`.** Documentation that nothing
  executes; 13.5 inlines what the skills need.

### Not automatable, kept with a manual check

- The last done-criterion of Phase 10. Whether a restricted machine refuses an
  unlisted marketplace needs a real managed-settings install. It is recorded
  as a manual step, with the command and its expected refusal, in the team-rollout
  README.

---

## Effort

| Phase | Estimate |
|---|---|
| 8 | 4–6 h |
| 9 | 14–18 h (9.2 and 9.4 carry most of it) |
| 10 | 3–4 h |
| 11 | 6–8 h |
| 12 | 10–14 h, plus about $60 in eval runs per full pass |
| 13 | 10–12 h |
| 14 | 12–16 h |
| 15 | 1 h |
| **Total** | **roughly 60–80 h**, similar to the first iteration |

The shortest path to a toolkit that is safe to show: **8.1 → all of Phase 9 →
10 → 11.4 → 13.2 and 13.9**. That covers the two Critical findings, the
injection path, the wrong-tree hooks (9.7), the policy template, and the
wording that blocks publication.
