# delivery-quality

Verification before you trust a change.

```
/plugin install delivery-quality@pacoromerodev
```

## Components

| Component | Type | Fires when |
|---|---|---|
| `verify-changes` | Skill | You ask to verify, double-check or confirm a change, or are about to commit or open a PR |
| `code-reviewer` | Subagent | You ask for a review or a second opinion, or `/review` is run |
| `guard_secrets` | PreToolUse hook | Always, on `Write`, `Edit`, `NotebookEdit` and `Bash` |
| `guard_destructive` | PreToolUse hook | Always, on `Bash` |
| `test_gate` | Stop hook | Only in projects that opt in |
| `/verify`, `/review` | Commands | Typed |

## verify-changes

Three checks, in order: run the project's tests, read the whole diff, and check
whether any test was weakened, skipped or deleted. The third is the one that
matters, because a passing suite hides it.

The report always ends with a verdict and a **Not verified** section. Naming
what was not covered is what makes the rest of the report worth reading.

## code-reviewer

Read-only. It has no edit tools and does not get them: if a fix is obvious, it
describes the fix and the main thread applies it.

Findings come back as Blocking / Worth fixing / Noted, each anchored to a file
and line, each stating the input or state that makes it fail. Style preferences
are not findings. The **Obstacles encountered** section is required — a
subagent returns only its summary, so an unstated gap is an invisible one.

## guard_secrets

Blocks a write when it would put a real credential on disk.

**Patterns:** AWS access keys, Anthropic and OpenAI keys, GitHub and Slack
tokens, Stripe live keys, Google API keys, private key blocks, JDBC and other
connection strings carrying a password.

**Paths:** `.env` and its variants, `credentials`, `.aws/credentials`,
`id_rsa`, `id_ed25519`, `.npmrc`, `.pypirc`, `secrets.yaml`,
`application-prod.yaml` — whether they are named by a Write, a redirect, `tee`,
`cp`, `mv` or `install`, with `/` or `\` separators. `.env.example` and its
siblings are templates, so only their content is checked.

**Also blocked:** `.claude/secret-guard-allow` and
`.claude/destructive-guard-allow`. Both guards' exception lists are the user's
to edit; an agent that can write them can switch the guard off.

**Not scanned:** a shell command that only reads or searches — `grep`, `rg`,
`git log -S`, `cat` — and writes no file. Looking for a leaked key is not
leaking it. Anything that writes, including `aws configure set`, is scanned.

**Allowed through:** values that are obviously not real — `EXAMPLE`,
`PLACEHOLDER`, `REDACTED`, `CHANGEME`, `DUMMY`, `FAKE`, `YOUR_*`, `<angle
brackets>`, `${VARS}`, `$UPPERCASE`, five or more `x`. These markers are
**case-sensitive** on purpose: lowercase `example` appears in the reserved
documentation domains, and matching it would let a real password through in
`mongodb://admin:hunter2@cluster0.example.net`.

If the guard itself fails — malformed payload, unexpected shape, any exception
— it exits clean and lets the call through. A guard that silently stops
guarding is bad; a guard that bricks the session is worse.

## guard_destructive

Blocks a command when the damage outlives the session. The test is not whether
a command is dangerous — most useful ones are — but whether you can get the
work back afterwards.

| Blocked | Why |
|---|---|
| A force-push to main, master, develop, release or production, in any spelling: `--force`, `-f`, `+main`, `--force-with-lease` | Rewrites history other people have pulled. `--force-with-lease` only protects against work you have not fetched, so to a shared branch it is not an alternative |
| `git push --mirror`; deleting a protected remote branch | Overwrites or removes branches other people build on |
| `git reset --hard`, `git checkout .`, `git restore .` over modified tracked files | Names the files it would discard. Untracked files survive these commands, so they do not count |
| `git clean -f…` | Deletes untracked files, including local config never meant to be committed. `git clean -n` (a dry run) passes |
| `git branch -D` | Force-deletes an unmerged branch; `-d` refuses instead |
| `rm -r` / `find … -delete` outside the project directory, in any flag order, including `$VAR` targets | An agent should not reach past the project it was given |
| `DROP` / `TRUNCATE` / `DELETE FROM` without `WHERE`, sent to a database client | Unless the connection arguments name a test, dev, local, staging or sandbox target |
| `chmod 777`, `mkfs`, `dd` to a device | |
| bulk `kubectl delete`, `terraform -auto-approve` | Outside an obviously non-production context |

**How commands are read.** The guard does not match one pattern against the
whole string. It splits the line into the commands the shell would run (on
`;`, `&&`, `||`, `|`, `&` and unquoted newlines), tokenises each one as the
shell would, and drops wrappers such as `sudo`, `env` and `VAR=value`. So flag
order and quoting do not change the verdict. Text that only travels as data —
a heredoc written to a file, a quoted commit message — is not mistaken for a
command. Text that runs — `bash -c "…"`, `$(…)`, a heredoc fed to a shell — is
checked like any other command. SQL is read from inside the quotes, because
that is how it reaches `psql` or `mysql`.

**Environment markers** count only in the database client's connection
arguments, never in a redirect such as `2>/dev/null`. A letter on either side
breaks the match: `app_test`, `dev-cluster` and `localhost` count, while
`developer` and `latest` do not.

Relax the guard per project in `.claude/destructive-guard-allow`, one regex per
line. A rule exempts only the command it matches, not every command chained
after it on the same line.

## test_gate

Inert until a project opts in:

```bash
mkdir -p .claude && touch .claude/test-gate     # runner auto-detected
```

Detects Maven, Gradle, npm, pytest, Go and Cargo from the files present. For
anything else, or to keep a slow suite out of the way of docs-only sessions:

```json
{
  "command": ["./scripts/ci-test.sh", "--fast"],
  "timeout": 600,
  "only_when_changed": ["src/**", "pom.xml"]
}
```

in `.claude/test-gate.json`. A `.claude/test-gate.sh` executable works too.

On failure it prints the **first** failure with surrounding context, not the
tail of the log — on Maven and Gradle the last lines are the build summary,
which says nothing about what broke.

It never re-enters itself — it checks `stop_hook_active`, without which the gate
fires again on the stop that follows its own feedback and the session cannot
end. A timeout or a crash lets the session end.

Override the 900-second limit with `CLAUDE_TEST_GATE_TIMEOUT`.

## Tests

```bash
plugins/delivery-quality/tests/run.sh
```

88 fixture cases across both guards and the gate: secrets that must block,
paths that must block, destructive commands that must block, legitimate values
and commands that must pass, and malformed input that must fail open. Adding a
pattern without a fixture — in both directions — is not done.

## Evals

```bash
claude plugin eval plugins/delivery-quality --scaffold --allow-tools Bash
```

Four cases:

- **verify-fires** — a scaffolded repo whose suite is green while the change is
  broken: a clamp caps the discount at 50%, and the test that would have caught
  it was rewritten from an exact assertion to an `isinstance` check. Trusting
  the green suite fails the case.
- **verify-not-fired** — a plain question about the project layout. Running the
  whole verification procedure here is a false positive, and the cost lands on
  every unrelated question.
- **review-format** — the review structure must survive being relayed, including
  the "Obstacles encountered" section.
- **guard-blocks-destructive** — a force-push to main is blocked; the model must
  relay the reason and take an alternative rather than retry the command.

**Known environment limitation:** on a machine where `~/.docker` contains a
symlink — which Docker Desktop's WSL integration creates for `contexts` and
`features.json` — the Bash sandbox cannot run, and any Bash-granting eval fails
before it starts. This is a machine constraint, not a case defect. Run those
cases in CI (`.github/workflows/evals.yml`), or on a machine without that
layout. Cases that need no Bash run locally.

## Requirements

Python 3.8+ on `PATH`. Standard library only — no `pip install`, enforced in CI.
