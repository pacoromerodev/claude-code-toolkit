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
| `restore_state` | PostCompact + SessionStart hook | After compaction, and on a new or resumed session |
| `scope-task` | Skill | A wide, vague or open-ended request |
| `claude-md-doctor` | Skill | Rules in CLAUDE.md are being ignored, or one needs writing |
| `/handoff`, `/context` | Commands | Typed |

## The state cycle

`save_state` writes `.claude/state/<session_id>.md` holding the branch, the
uncommitted and staged files, the diffstat, the last five commits, and any
stashes. `restore_state` reads it back and emits it as
`hookSpecificOutput.additionalContext`.

Three decisions worth knowing:

- **Namespaced by session id.** Two sessions in one repository would otherwise
  overwrite each other's snapshot, and the second one would restore the first
  one's tree.
- **A snapshot over 24 hours old is not restored.** It describes a tree that has
  moved on, and presenting it as current would be worse than silence. The hook
  mentions the file exists and stops there.
- **A `/handoff` note outranks everything measured.** A person wrote it on
  purpose; git status is just the truth about files.

Add `.claude/state/` to your `.gitignore`.

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

20 assertions. The auditor must find every planted fault in the bad fixture and
**report nothing at all** on the good one. The save → restore cycle runs end to
end in a throwaway git repository: snapshot written, branch and untracked files
and commits recorded, handoff note picked up, context emitted with its caveat,
both hooks surviving a malformed payload, and restore staying silent when there
is nothing to restore.

## Evals

```bash
claude plugin eval plugins/context-discipline --scaffold --allow-tools Bash
```

- **claude-md-rewrite** — a CLAUDE.md of unfollowable rules; the review must
  rewrite them, not list them.
- **scope-before-code** — "clean up the payment module", where a caller in
  another package depends on the method that would change.
- **not-fired** — a one-word typo fix, which must not trigger a planning
  ceremony.

## Requirements

Python 3.8+ on `PATH`. Standard library only. `PostCompact` requires Claude
Code 2.1 or later.
