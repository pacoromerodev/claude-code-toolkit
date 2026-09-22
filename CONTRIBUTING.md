# Contributing

These are the rules a change to this repository is reviewed against. Each one
exists because the opposite failed somewhere.

## Design rules

**A report is not evidence.** A skill or subagent ends with command output, a
diff, a file path — not with "everything looks good". If a component cannot
produce evidence, it should say what it could not check.

**Name what you did not check.** Every reporting component carries a section
for its own gaps: "Not verified" in `verify-changes`, "Obstacles encountered"
in `code-reviewer`. A subagent returns only its summary, so an unstated gap is
invisible to whoever reads it.

**The output format is the design.** For a subagent, deciding what it returns
matters more than describing what it is. Fixed headings, kept even when empty —
an empty section is information, a missing one is ambiguity.

**No persona agents.** "You are a senior security expert" adds nothing a task
description does not. Write what it does, what it may touch and what it
returns.

**Minimum tools.** Grant the smallest set that does the job. A reviewer gets
`Read`, `Glob`, `Grep`, `Bash` and no edit tools. Widening the set is a change
that needs a reason in the commit message.

**Hooks fail open.** A guard that crashes lets the call through. Wrap the
entry point, exit 0 on any unexpected error. Determinism is worth having only
while it cannot brick a session.

**Exit 2 is the only blocking code.** It returns stderr to Claude as feedback,
so the model sees the reason and can correct itself. Exit 1 does not block.
Anything else is non-blocking.

**Standard library only, on Python 3.8.** Hooks run on a machine where
nothing has been installed, using whatever `python3` is already there — a
stock macOS still answers 3.9. The floor is declared once, as `MINIMUM` in
`.github/scripts/check_stdlib_only.py`, which also fails if the CI matrix
stops testing it. `tomllib`, `zoneinfo` and `graphlib` are standard library
and still rejected: they arrived after the floor, so they pass on the runner
and fail on the machine that matters.

This binds `plugins/*/scripts`; a CI script under `.github/scripts` runs only
on a runner and may install what it needs, as the settings schema check does.
Widening the allowed set is a deliberate edit to that script, not an accident.

**Every rule is checkable.** "Handle errors properly" is not a rule. "Do not
catch an exception without either re-raising or logging it with context" is.
If a reviewer cannot tell whether a rule was followed, rewrite it.

## Adding a plugin

```
plugins/<name>/
├── .claude-plugin/plugin.json     # name must equal the directory
├── README.md                      # required
├── CHANGELOG.md                   # required
├── skills/<skill>/SKILL.md
├── agents/<agent>.md
├── commands/<command>.md
├── hooks/hooks.json
├── scripts/*.py
├── tests/{run.sh,fixtures/*.json}
└── evals/<case>/{case.yaml,graders/*.md}
```

Then add the entry to `.claude-plugin/marketplace.json` with a matching `name`,
`source` and `version`.

In hook commands use `${CLAUDE_PLUGIN_ROOT}`, never a relative path — the
plugin runs from wherever it was installed, not from this repository.

## Before opening a pull request

```bash
claude plugin validate .                      # marketplace manifest
claude plugin validate plugins/<name>         # plugin manifest
python3 .github/scripts/check_consistency.py  # entries and versions agree
python3 .github/scripts/check_stdlib_only.py  # no third-party imports
python3 .github/scripts/check_eval_cases.py   # every eval case can pass
python3 .github/scripts/check_hooks.py        # hooks point at scripts that exist
python3 .github/scripts/check_names.py        # no two components share a name
python3 .github/scripts/check_workflows.py    # workflows scoped, pinned, no interpolated shell
python3 .github/scripts/check_course_wording.py # no sentence lifted from the notes
python3 .github/scripts/check_eval_coverage.py  # two cases per skill, one negative
python3 .github/scripts/validate_settings_schema.py  # settings match the published schema
plugins/<name>/tests/run.sh                   # fixture tests
```

CI runs all of these. Eval suites are not part of the pull-request gate —
they cost money and need a credential — so run them by hand before a release:

```bash
scripts/run-evals.sh [plugin ...]             # results outside the repo, never published
```

The runner evaluates the working copy, one case at a time. `claude plugin
eval` refuses any Bash-granting run while the Docker credential store holds a
symbolic link (common on WSL with Docker Desktop). When that is the case the
runner skips the cases tagged `needs-bash` and lists them as NOT RUN. It never
works around the check: move the store's contents into a plain directory if
you need those cases.

## Writing a skill

The description is what decides whether the skill fires. It answers two
questions — what this does, and when to use it — and it is the first thing to
rewrite when a skill does not trigger.

Keep `SKILL.md` under 500 lines. Anything long goes to `references/`, loaded
on demand. Anything executable goes to `scripts/`, which runs without being
read into context.

Every skill needs at least three eval cases: two prompts that should trigger it,
worded differently from the description, and one in the same domain that should
not. The negative case is not optional — a skill that fires on everything costs
context on every unrelated turn.

`check_eval_coverage.py` counts them, from the tags: the component's name plus
`skill`, `subagent` or `hooks`, and `negative` for the case where nothing
should fire. A tag naming no component in the plugin is a typo, and it is
reported as one — a mistyped tag is a case that counts towards nothing.

## Writing a hook

Read the payload from stdin, write feedback to stderr, exit 2 to block.

Every branch that can block needs a fixture in `tests/fixtures/`, and so does
every value that must pass. Adding a pattern without both is incomplete: the
one bug the fixture suite has caught so far was an allowlist that let a real
password through, and only the passing cases could have found it.

## Releasing

1. Update the plugin's `CHANGELOG.md`
2. Bump `version` in `plugin.json` **and** in the marketplace entry — they must
   agree or the tag is refused
3. `claude plugin tag plugins/<name>`
4. Push the tag

## Never in this repository

Employer names, internal hostnames or URLs, repository or ticket identifiers,
client-specific branch conventions. Real credentials in fixtures — use the
`EXAMPLE` and `${PLACEHOLDER}` forms the guard already recognises. Text copied
from Anthropic Academy: the concepts are free to use, the wording is not.

`check_course_wording.py` checks the last one against
`.github/scripts/data/course-shingles.txt` — hashes of every five-word run in
the notes, no text, so the check works without the notes being public.
Regenerate it from a local checkout when the notes change:

```bash
python3 .github/scripts/check_course_wording.py --update --notes <notes dir>
```

It sees verbatim English only. A paraphrase, and anything translated out of
the Spanish prose, stays a manual read before publication.
