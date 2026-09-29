---
name: verify-changes
description: Verify that a change actually works before trusting it. Runs the project's tests, reads the full diff, and checks that no test was weakened, skipped or deleted to make the suite pass. Use after implementing a feature or a fix, before committing, before opening a PR, or whenever the user asks to verify, double-check or confirm that changes are correct.
---

# Verify changes

A summary of work is not evidence that the work is correct. This skill replaces "I implemented X and the tests pass" with a report backed by command output and the diff.

Run the three checks in order. Do not skip a check because an earlier one looked fine.

## 1. Run the tests

**If the project says how to run them, that wins.** Check first:

| File | What to run |
|---|---|
| `.claude/test-gate.json` | The `command` it names |
| `.claude/test-gate.sh` | That script |

Those are what this project's own gate runs, so a verification that runs
something else is verifying a different thing.

Otherwise detect the runner from the files present, in this order:

| File | Command |
|---|---|
| `pom.xml` | `mvn -q test` |
| `build.gradle` / `build.gradle.kts` | `./gradlew test` |
| `package.json` with a `test` script | `npm test` |
| `pyproject.toml` / `pytest.ini` / `tests/` | `pytest -q` |
| `go.mod` | `go test ./...` |
| `Cargo.toml` | `cargo test` |

If several match, run the one that covers the changed files. If none match, say so plainly and move to step 2 — do not invent a command, and do not report the change as verified.

Capture the real output. A failing suite ends the verification: report the failures and stop.

## 2. Read the diff

```bash
git status --porcelain
git diff HEAD
git ls-files --others --exclude-standard
```

**`git diff` does not show a file that was never added.** A change made
entirely of new files produces an empty diff, and a verification that reads
only the diff reports nothing wrong with code it never saw. Read every
untracked file in full — the third command lists them — and treat it as a
hunk that is all additions.

Read every hunk, not the summary. You are looking for what the change does beyond what was asked:

- Debug output, commented-out code, `TODO` left behind
- Hardcoded values that should be configuration, credentials or tokens of any kind
- Error paths that swallow the error, empty `catch` blocks, broad `except`
- Changes to files nobody asked you to touch
- Behaviour changes not covered by any test

## 2a. If the change adds a dependency

A package name that looks right is not a package that exists. A generated
import, a name half-remembered from another ecosystem, and a typo all read the
same in a diff — and a plausible name that nobody owns is also how a
dependency gets taken over later.

For each package the change introduces, confirm it resolves:

| Ecosystem | Check |
|---|---|
| npm | it is in `package-lock.json`, or `npm view <name> version` answers |
| Python | it is in the lockfile (`poetry.lock`, `uv.lock`, `requirements.txt` with a pin), or `pip index versions <name>` answers |
| Maven / Gradle | the coordinates appear in the lockfile, or resolve from the declared repositories |
| Go | `go mod download <module>` succeeds |
| Cargo | it is in `Cargo.lock`, or `cargo search <name>` answers |

Report a package that does not resolve as a finding, with the name and where
it was introduced. Say what you checked against — the lockfile, or the
registry — because "it installs on my machine" and "it is in the lockfile" are
different facts.

## 2b. If the change touches a workflow

A workflow runs with nobody watching, and a change to one is not covered by
any test. When the diff includes `.github/workflows/`, check each of these and
report what you found:

- **`permissions:`** is declared. Without it the job gets the repository
  default, which is usually more than it needs.
- **Checkout does not keep the token.** `persist-credentials: false`, unless
  something later genuinely pushes.
- **Nothing is interpolated into a shell.** A `${{ }}` inside a `run:` block
  is pasted in as text before the shell sees it, so an issue title or a
  comment body becomes part of the command. Pass values through `env:`.
- **Versions are pinned** — the action, and any CLI installed by the job.
  An action is pinned only by a full commit SHA, with the release as a
  comment: `@main` is whatever it holds today, and a tag such as `@v4` is a
  name its owner can move to other code. A CLI is pinned by an exact version.
- **If the job runs Claude:** a turn cap, tools granted narrowly rather than
  as whole tools, and no permission bypass. Unattended is exactly where those
  matter.

Check these by reading the workflow file; this plugin ships no script for it.

## 3. Check the tests were not weakened

This is the check that matters most, because it is the one a passing suite hides.

```bash
git diff HEAD -- '**/test/**' '**/tests/**' '**/*_test.*' '**/*.test.*' '**/*Test.java'
```

Flag every one of these:

- A test deleted, or its body replaced by a `return` / `pass`
- `@Disabled`, `@Ignore`, `.skip`, `xit`, `@pytest.mark.skip`, `t.Skip` added
- An assertion removed, or loosened — `assertEquals` becoming `assertNotNull`, an exact value becoming `any()`, a range widened
- A timeout raised to make a flaky test pass
- Expected values edited to match what the code now produces, rather than what it should produce

If the implementation and its tests changed in the same commit, state explicitly which assertions changed and why.

## Report

Report in this shape, always, even when everything passes:

```
## Verification

**Tests:** <command run> → <N passed, M failed, K skipped>
**Diff:** <N files, +X / -Y>

### Findings
- <finding, with file:line and what makes it a problem>
(or: none)

### Tests
- <what the new or changed tests actually assert>
- <weakened assertions, or: no test was weakened>

### Not verified
- <what this check could not cover: no integration tests, no runner found,
   behaviour that needs a running service, manual steps>

**Verdict:** verified / verified with findings / not verified
```

The "Not verified" section is required and is never empty in practice. Naming what you did not check is what makes the rest of the report trustworthy.

Do not end with "everything looks good". End with the verdict and the evidence behind it.
