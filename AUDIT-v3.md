# Audit — third iteration (2026-09-28)

Continues [`AUDIT.md`](AUDIT.md) and [`ROADMAP-v2.md`](ROADMAP-v2.md). Read
against the 22 courses as they sit in the academy repository — the Spanish
notes in `web/src/` and, for the first time, the lessons in their original
English in `cursos/` — and against the rules this repository sets itself in
`CONTRIBUTING.md` and `CLAUDE.md`.

Every finding marked **Fixed** is a commit on this branch, validated by the
commands in `CLAUDE.md`. Everything else is a recommendation with the command
or evidence that would settle it.

## Baseline

Before any change, on `main` at `84da89f`, every command in `CLAUDE.md`
exited 0: six manifests validate, the eight CI checks pass, the auditor is
clean over 9 skills and 2 agents, 335 fixture tests pass across the five
plugins and 73 across the CI scripts, route and runner tests pass, shellcheck
is clean, the settings match the schema. The eval ledger has 30 of 30 cases
measured on `claude-opus-5-5`, graded by `claude-sonnet-5`.

The repository is in good shape mechanically. What follows is about what the
checks could not see.

## Findings fixed on this branch

### F1 — The wording check could not see the English lessons *(High, fixed)*

`check_course_wording.py` was built from `web/src`, whose prose is Spanish.
Its data file held 350 fingerprints, taken mostly from code blocks and
prompts. The academy repository also holds every lesson in English under
`cursos/`, which is where a borrowed sentence would come from, and the script
could not read it: `--update` took one directory and did not recurse.

Built from both sources, the data file holds 73,333 fingerprints, and 20 runs
in `plugins/` matched. Most were stock phrases about changing a single variable per run, but
`plan-rollout`'s decision-owners table tracked the enterprise course's own
table row by row. All 20 are reworded. `--notes` now repeats and recurses,
and the scan also covers `docs/`, the README and CONTRIBUTING, which are
published as much as `plugins/` is; three runs in `docs/anatomy.md` matched
and are reworded.

Regenerate with:

```bash
python3 .github/scripts/check_course_wording.py --update \
    --notes ../anthropic-academy-es/web/src \
    --notes ../anthropic-academy-es/cursos/_bundles
```

### F2 — The local gate was weaker than CI *(Medium, fixed)*

`CLAUDE.md` ran `check_eval_coverage.py` and `check_course_wording.py`
without `--enforce`, so both reported and exited 0 on a violation CI fails
on. Its loops ended in `|| break`, which leaves a loop's status at 0. Both are
corrected, and the `check_claude_md.py` step CI runs on `CLAUDE.md` is listed.

### F3 — A subagent granted a tool it never uses *(Medium, fixed)*

`tool-schema-review` had `Bash`. It judges a tool's name, description and
schema, and its instructions never run a command. CONTRIBUTING's
minimum-tools rule asks for a reason to widen a set; there was none.

### F4 — Two components assumed they were running in this repository *(Medium, fixed)*

`verify-changes` told the model that `.github/scripts/check_workflows.py`
existed "in this repository". Installed in a user's project, it does not.
`code-reviewer` hard-coded `main` as the base of a branch review; it now takes
the named base, else `origin/HEAD`, and says which it used.

### F5 — Stale documentation *(Low, fixed)*

- README's *Layout* showed one plugin of five, and *Development* sent evals to
  a workflow removed on 2026-09-24.
- `docs/anatomy.md` said a command and a hook cost no context. A command's
  description is listed every session — the removal of the wrapper commands
  in Phase 13.12 saved tokens for exactly that reason — and a `SessionStart`
  hook's output is context, which is how `restore_state` works. MCP servers
  were missing from the table.

### F6 — CI hygiene *(Low, fixed)*

No job had a `timeout-minutes`, so a hung step held a runner for the six-hour
default; superseded runs were not cancelled; nothing proposed updates to the
pinned actions. Added `timeout-minutes`, a `concurrency` group and
`.github/dependabot.yml`. Every `plugin.json` now declares `license` and
`repository`.

## Recommendations, in order

### R1 — Re-measure what this branch changed *(before merging)*

The case fingerprints cover the case, not the plugin (ROADMAP-v2, *What
freshness cannot see*). This branch changed components the following cases
exercise, and only `rollout-order` will read as stale on its own:

| Changed | Cases to re-run |
|---|---|
| `tool-schema-review` (no Bash) | `api-patterns/tool-never-chosen` |
| `code-reviewer`, `verify-changes` | every `delivery-quality/review-*` and `verify-*` |
| `plan-rollout`, `settings-review`, `rollout-order` criteria | every `team-rollout` case |
| `claude-md-doctor`, `eval-harness` wording | `context-discipline/claude-md-rewrite` and `rules-nobody-follows`; `api-patterns/score-jumped-after-examples`, `bedrock-model-not-found` |

```bash
scripts/run-evals.sh --model claude-opus-5-5 delivery-quality team-rollout
scripts/run-evals.sh --model claude-opus-5-5 --stale
```

### R2 — Cut releases, or users never receive the fixes *(High)*

Every plugin has an `[Unreleased]` section that has grown since its last
version: the Phase 9 safety fixes, the removed commands, the new cases.
Claude Code decides whether an installed plugin needs updating from its
version, so a user who installed `delivery-quality@0.2.0` keeps the code they
installed until the version moves. Bump each plugin that has unreleased
changes (`plugin.json`, the marketplace entry and the changelog, in one
commit, as `CLAUDE.md` requires), and the marketplace `metadata.version`,
still `0.1.0`.

### R3 — Settle `api-patterns` before adding anything *(High)*

With Sonnet judging it scores 0.63 and **Δ −0.10**: the only plugin that
does worse than no plugin. ROADMAP-v2 leaves it open, pointing at
`--keep-temp` traces for `cache-ttl-mismatch`, `cache-silently-missing` and
`score-jumped-after-examples`. The rule that retired `java-spring` and
`mcp-builder` applies: a skill that does not beat the baseline after its
traces are read either gets fixed on that evidence or goes. `check_api_calls.py`
and `fuse.py` are scripts the model cannot replace; the prose skills are
what has to justify itself.

### R4 — Pin actions to a commit, not a tag *(Medium)*

`actions/checkout@v4` names a tag its owner can move. Pin each `uses:` to a
full commit SHA with the tag as a comment; Dependabot (added here) keeps
SHA pins current. Then make `check_workflows.py` reject a non-SHA ref, as it
already rejects `@main`. Not done here: this session could not read the
actions' repositories to take the SHAs.

### R5 — One Claude Code version for CI and for evals *(Medium)*

CI validates manifests with `@anthropic-ai/claude-code@2.1.278`; the evals in
the ledger ran on 2.1.281–2.1.282. Record the CLI version in the ledger next
to the model and judge, and bump the CI pin in the same commit as a
re-measurement.

### R6 — The `needs-bash` cases still have no home *(Medium)*

The guards, the test gate and the checkers are covered by 335 fixture tests
but not by an eval, because `claude plugin eval` refuses Bash without a
working sandbox and the cloud's nested sandbox gives false passes. A small
Linux VM with `bubblewrap`, `socat` and no `~/.docker` symlink, used only for
`run-evals.sh`, would close this. Until then, keep saying *not run*, as the
runner does.

### R7 — Components the courses suggest, not yet built *(Low; evaluate first)*

Each is a candidate for an existing plugin, not a new one — AUDIT §5's
argument against more always-on context still holds.

- **`InstructionsLoaded` audit** (`claude-code-in-action`, lesson 5, which
  lists the event). `claude-md-doctor` reasons about a CLAUDE.md in isolation;
  a hook on this event could record which instruction files actually loaded,
  in the style of skill-forge's routing log.
- **Redact, not only block** (ROADMAP-v2 14.3 is already there; the lesson's
  `updatedInput` example is the pattern). Worth measuring whether opt-in
  redaction changes how often the model routes around the secret guard.
- **Hook `if` clauses** (same lesson) were considered for narrowing
  `guard_destructive` and rejected: a narrower match is exactly how a guard
  misses a form it should block (AUDIT C2). Measured cost of running both
  guards on every Bash call is under 40 ms each; not worth the risk.

### R8 — Smaller items

- `scope-task` lists `TodoWrite` in `allowed-tools`. Pre-approving it does
  nothing (it never prompts), and recent Claude Code versions replace it with
  task tools. Verify against the current tools reference, then drop it.
- The fingerprint file is now ~950 KB. Acceptable for a data file; if it
  grows, a sorted fixed-width binary format would halve it.
- The README details only `delivery-quality`. Either one short section per
  plugin, or none, with every plugin linking to its own README.

## Plan to go public — decided 2026-09-29

The owner's decisions: the repository **goes public**, and **no evals are
run** as part of getting there. Anything that needs a measurement is stated
as unmeasured rather than decided. Each step below is one commit, validated
by the block in `CLAUDE.md`; a new or tightened check ships with one fixture
that must fail and one that must pass.

### Branches

| Branch | State | Action |
|---|---|---|
| `main` | `84da89f`, PRs #1–#17 merged (#6 was a CI proof, closed) | — |
| `claude/peaceful-curie-cwduai` | This audit, open as pacoromerodev/claude-code-toolkit#18 | Merge once CI is green |
| `claude/audit-and-fix` | `fc84f6d`, the initial commit and PR #1's base. **Confirmed in `main`'s history** | Delete — approved by the owner. **Pending**: needs `git push origin --delete claude/audit-and-fix` |

### Answers already given

- **Employer terms** (ROADMAP.md:255, checklist item 1): the owner confirms
  none were ever added. The history scan below still runs, for secrets and
  local paths, which do not depend on that answer.

### Pending, in order

| # | Step | Done when |
|---|---|---|
| P1 | **Freshness covers the component.** `eval_ledger.py`'s fingerprint also hashes the file of the component a case names in `tags:` (`skills/<name>/SKILL.md`, `agents/<name>.md`) | A freshness fixture whose `SKILL.md` is edited after measurement reads "changed since"; on this branch, the cases in R1 list as unmeasured |
| P2 | **CLI version in the ledger** (R5). `record_measurement.py` and `run-evals.sh` store `claude --version` next to model and judge; the CI pin moves from 2.1.278 to 2.1.282 | `scripts/tests/run-evals.test.sh` asserts the field |
| P3 | **Measured status in each plugin README**, from the ledger as it stands (Sonnet judge, 2026-09-26). `api-patterns` is labelled **experimental** there and in its marketplace description (R3 stays open) | README and `marketplace.json` agree; `check_consistency.py` passes |
| P4 | **History scan** (checklist items 1–2): the patterns in `guard_secrets.py`, reused, over `git log -p --all`; GitHub secret scanning; `/home/` and `/Users/` paths; e-mails other than the public one; internal paths in `plugins/*/scripts` and `plugins/team-rollout/settings` | No hit, or each hit listed here with its resolution. Rewriting history, if ever needed, is the owner's decision |
| P5 | **Actions pinned to a SHA** (R4), and `check_workflows.py` rejects any non-SHA ref | Bad and good workflow fixtures; `validate.yml` passes |
| P6 | **`SECURITY.md`**: how to report a guard bypass. AUDIT.md documents bypasses Phase 9 fixed; link the fix | File present, linked from the README |
| P7 | **Wording check covers the root `.md` files** (AUDIT, ROADMAP, ROADMAP-v2, this file), with an allowlist for course titles such as "Claude with the Anthropic API". Reword the few real hits, two stock phrases among them | `check_course_wording.py --enforce` exits 0 over the wider scope |
| P8 | **Manual read** (checklist item 3; the check cannot see a paraphrase of Spanish prose): `rag-retriever/SKILL.md` and `plan-rollout/SKILL.md` against their courses | Result recorded in this file |
| P9 | **Releases** (R2): delivery-quality 0.2.0 → 0.3.0 (commands removed), context-discipline, api-patterns and team-rollout 0.1.0 → 0.2.0, skill-forge if it has unreleased changes; marketplace `metadata.version` 0.1.0 → 0.2.0; a tag `<plugin>-v<version>` per release | One commit per plugin touching `plugin.json`, `marketplace.json` and `CHANGELOG.md` together |
| P10 | **README for strangers** (checklist item 5, R8): one short section per plugin or links only; install steps tested from a clean clone; a status section linking the measurements | Followed end to end from a fresh clone |
| P11 | **`TodoWrite` in `scope-task`** (R8): check the current tools reference, drop it if it is gone or needs no pre-approval | `audit_skills.py` clean |
| P12 | **Publish** — the owner's step: final checklist here, repository visibility set to public, then from another account `/plugin marketplace add pacoromerodev/claude-code-toolkit` and `/plugin install delivery-quality@pacoromerodev` | The install works for someone who is not the owner |

### Done — 2026-09-29

Each step one commit on `claude/peaceful-curie-cwduai`, each through the
`CLAUDE.md` block.

| # | Result |
|---|---|
| P1 | Done. Ledger entries carry a `components` fingerprint, backfilled from the tree of the commit that recorded each one. No component changed between those commits and the merge before this audit, so what now reads as changed is exactly what this audit touched: 19 cases, then 2 more once P11 changed `scope-task` |
| P2 | Done. `cli` is recorded; CI installs 2.1.282, on which all six manifests validate |
| P3 | Done. Every plugin README has a *Measured* section; `api-patterns` is labelled experimental in four places |
| P4 | **No secret, no internal path.** The 20 patterns of `guard_secrets.py` over all 93 commits found 13 distinct values, every one a deliberately fake key in a test fixture, an eval scaffold or a documentation example. `/home/user` is the fixtures' generic path, `/Users/alice` an example. GitHub's scanner takes pasted snippets only, and 1 MB of added lines is not practical through it; not run. **One decision for the owner:** 140 commits carry a personal e-mail address as author. It becomes public with the history. Keeping it is a choice; replacing it means rewriting every commit, which only the owner can decide |
| P5 | Done. checkout and setup-node at v4.4.0, setup-python at v5.6.0, by SHA; any other ref fails the check. Newer majors exist (v7); Dependabot will propose them |
| P6 | Done. `SECURITY.md`, linked from the README. **For the owner:** enable *private vulnerability reporting* in the repository's security settings, or its reporting instruction leads nowhere |
| P7 | Done. Nine runs in five root files reworded; the 22 course titles are allowed as citations |
| P8 | Done, and clean. `rag-retriever`'s contextual-retrieval section reuses the idea with its own prompt, structure and example. `plan-rollout`'s postures, spend rules and new-capability questions follow the enterprise course's structure in this plugin's words, and its worked example (a scheduled-task surface) is not the course's (a Slack integration) |
| P9 | Done. delivery-quality 0.3.0; context-discipline, api-patterns, team-rollout 0.2.0; marketplace 0.2.0. Tags `<plugin>-v<version>` wait for the merge, so they point at commits on `main` |
| P10 | Done. README has a quick start and a status table (version, always-on context, measured Δ). Installed from a clean clone into an empty home: all five plugins install and report their new versions |
| P11 | Done. Claude Code 2.1.284 ships both `TodoWrite` and the task tools; neither asks for permission, so the entry did nothing. Removed |
| P12 | Waiting, by the owner's decision: the repository stays private until the remaining improvements are in |

`anthropic-academy-es` **stays private**: it holds the lessons verbatim, and
it must remain readable locally to regenerate the fingerprints.

### Out of this plan — each needs an eval

- R1: re-measure the cases this branch changed (P1 makes them visible).
- R3: keep or retire `api-patterns`.
- R6: a machine that can run the `needs-bash` cases.
- R7: new components; CONTRIBUTING requires measured cases for them.

## On `anthropic-academy-es`

Not changed; these are notes for it.

- `cursos/` and `quizzes.json` hold the lessons and quiz answers verbatim.
  The repository is private and should stay so, and the README could say why.
  Its two artifact links are private too, which the README states correctly.
- It is now a build input for this repository's wording check. Adding a line
  to its README pointing at the regeneration command in F1 keeps the two from
  drifting.
- The catalogue at academy.claude.com could not be read from this session
  (the network policy blocks it), so whether new courses have appeared since
  the repository was last scraped (2026-09-20) is **not verified**. If they
  have, re-scrape, then regenerate the fingerprints.

## Not verified

- No eval was re-run. R1 lists what should be.
- `academy.claude.com` was unreachable; the course set is the 22 in the
  academy repository.
- The claim in R2 about how updates are detected follows the plugin
  documentation's description of versioning; it was not tested against an
  installed copy here.
- `scope-task`'s `TodoWrite` (R8) was not checked against the current tools
  reference.
