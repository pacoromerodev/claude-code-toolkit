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
in `plugins/` matched. Most were stock phrases ("one thing at a time"), but
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
