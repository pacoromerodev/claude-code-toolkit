# context-discipline

Keep the working state that compaction blurs.

```
/plugin install context-discipline@pacoromerodev
```

## The idea

Compaction summarises a conversation, and a summary is lossy in a specific way:
it keeps the narrative and drops the particulars. Which branch. Which files are
half-edited. What the last commit actually was.

None of that needs to be *remembered*, because it can be **measured**. So the
hooks here do not try to preserve the conversation — they take a snapshot of the
working tree before compaction and hand it back afterwards.

## Components

| Component | Type | Runs on |
|---|---|---|
| `save_state` | PreCompact hook | Every compaction, manual or automatic |
| `restore_state` | SessionStart hook, `compact` matcher | Right after a compaction, in the session that was compacted |
| `scope-task` | Skill | A wide, vague or open-ended request |
| `claude-md-doctor` | Skill | Rules in CLAUDE.md are being ignored, or one needs writing |
| `/handoff`, `/context-budget` | Commands | Typed |

## The state cycle

`save_state` records the branch, the uncommitted and staged files, the
diffstat, the last five commits and any stashes. `restore_state` reads it back
and emits it as `hookSpecificOutput.additionalContext`.

Four decisions worth knowing:

- **The snapshot lives outside the repository**, in the plugin's own data
  directory (`${CLAUDE_PLUGIN_DATA}`), keyed by repository and session id. A
  file written inside a working tree gets committed and cloned, and would then
  be read back as if this session had produced it. Nothing to gitignore.
- **Only the session that was compacted gets its snapshot back**, and only
  through `SessionStart` with the `compact` matcher. `PostCompact` receives the
  summary but has no way to add context, so a hook there is discarded.
- **A snapshot over 24 hours old is not restored**, and one from another
  session is never restored at all.
- **The `/handoff` note is read live at restore time**, not frozen into the
  snapshot, and it is labelled as written by the assistant, with its date. It
  is reasoning git cannot show — not a measurement, and not more trustworthy
  than one.

## CLAUDE.md auditing

```bash
python3 plugins/context-discipline/scripts/check_claude_md.py CLAUDE.md
```

CLAUDE.md is **guidance, not configuration**: read, never executed, present in
full on every turn, and competing with the actual task. The failure modes follow
from that.

| Finding | Why the rule gets ignored |
|---|---|
| Over 200 lines (error past 400) | The tail stops being read |
| More than ten IMPORTANT / ALWAYS / NEVER | Emphasis is a budget; spent everywhere it signals nothing |
| "properly", "best practices", "clean code" | A rule nobody can verify was followed is not a rule |
| Prohibition with no alternative | Closes one door, opens none, gets worked around |
| Broken `@import` | Contributes nothing, silently |
| Large `@import` | An import is expanded **inline** — it does not save context |

The last one is the most commonly believed wrong thing about CLAUDE.md.
Splitting a long file across imports changes where you read it, not what it
costs.

## Tests

```bash
plugins/context-discipline/tests/run.sh
```

30 assertions. The auditor must find every planted fault in the bad fixture and
**report nothing at all** on the good one. The save → restore cycle runs end to
end in throwaway repositories: snapshot written outside the repository and
nothing written inside it, branch and untracked files and commits recorded, the
live handoff note attributed, the output kept inside the context cap, a
directory that is not a repository reported as such, and restore staying silent
for another session, at a fresh start, and for a state file planted inside the
repository.

## Evals

```bash
claude plugin eval plugins/context-discipline --scaffold --allow-tools Bash
```

- **claude-md-rewrite** — a CLAUDE.md of unfollowable rules; the review must
  rewrite them, not list them.
- **scope-before-code** — "clean up the payment module", where a caller in
  another package depends on the method that would change.
- **context-cannot-be-measured** — "what percentage of the context have we
  used?". The answer must say it cannot measure that, and name `/context`.
- **not-fired** — a one-word typo fix, which must not trigger a planning
  ceremony.

## Requirements

Python 3.8+ on `PATH`. Standard library only. The `compact` matcher on
`SessionStart` requires Claude Code 2.1 or later.
