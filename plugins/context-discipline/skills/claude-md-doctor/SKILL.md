---
name: claude-md-doctor
description: Reviews a CLAUDE.md and rewrites the rules that get ignored — vague standards, prohibitions with no alternative, emphasis on everything, and length that pushes rules out of attention. Use when instructions in CLAUDE.md are not being followed, when writing or trimming one, or when the user asks to review their project instructions.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_claude_md.py *)
---

# Fixing a CLAUDE.md

CLAUDE.md is **guidance, not configuration**. It is read, not executed. Nothing
enforces it, so every line has to earn its place by being followed — and every
line competes with every other line, on every single turn.

That is the whole frame. Most fixes follow from it, including the two that
come before any rewriting:

**A rule that must never be broken does not belong here.** This file asks; a
`PreToolUse` hook that exits 2 refuses. "Never push to main" in CLAUDE.md is a
preference the model weighs against everything else in its context. The same
sentence as a hook is a fact about the machine. Move it, and delete the line —
a rule kept in both places is a rule nobody knows which copy governs.

**The best CLAUDE.md is the one that was never written.** Start with none. Add
a line the first time a correction repeats — the same fix, twice, for the same
reason. A file assembled from what someone imagined the model would get wrong
is mostly lines that have never been needed, competing with the ones that
have.

## Run the mechanical pass first

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_claude_md.py CLAUDE.md
```

It finds length, emphasis inflation, vague standards, prohibitions with no
alternative, broken and oversized imports, structure, rules a hook could
enforce instead, and emphasis buried in the middle of a long file. Then do
what it cannot: judge whether each rule is worth its space.

## The four rewrites

### Make it checkable

A rule a reviewer cannot verify is not a rule.

| Ignored | Followed |
|---|---|
| "Handle errors properly" | "Never catch an exception without either re-raising it or logging it with the failing input" |
| "Write good tests" | "Every new behaviour gets a test for its failure path, not only its happy path" |
| "Follow clean code principles" | "No method over 40 lines; extract rather than comment a section" |
| "Use appropriate logging" | "Log at WARN or above with the identifier that lets the event be traced; never log a request body" |

If you cannot write the checkable version, the rule may not be a real
preference — it may be a wish, and wishes make the file longer without making
anything better.

### Name the alternative

"Don't use field injection" closes a door and opens none. "Use constructor
injection; never `@Autowired` on a field" answers the question the prohibition
raises. A rule that leaves the next move open gets worked around.

### Spend emphasis like a budget

IMPORTANT, CRITICAL, ALWAYS, NEVER — past about ten, none of them signal
anything. Keep them for the handful of rules that genuinely override normal
judgement, and write the rest as plain statements.

### Cut length

Present on every turn, competing with the actual task. Under 200 lines stays
usable; past 400 the tail is decoration.

What to cut first:

- **Documentation.** How the system works belongs in the repo, and can be read
  on demand. CLAUDE.md is for what must be true every time.
- **Anything the tooling already enforces.** Formatting rules with a formatter
  configured. Lint rules with a linter.
- **Aspirations nobody follows.** If the codebase contradicts the rule, either
  the rule goes or the codebase does. Leaving both teaches that rules here are
  optional.

## Put what must hold at both ends

Within the file, position is signal. The opening lines are read with the most
attention and the closing lines are the most recent thing before the task, so
a rule that genuinely overrides goes first — and is worth repeating in one
line at the end. The middle of a long file is where instructions go quiet,
which is exactly where a rule migrates to as sections are appended above it.

## Imports do not save context

`@path/to/file.md` is expanded **inline**. The content is spliced in whole, so
splitting a long file across imports changes nothing about its cost — it only
changes where you read it.

Imports are for sharing one file across several CLAUDE.md files, not for
slimming one down.

## The four locations

Managed policy → user (`~/.claude/CLAUDE.md`) → project (`./CLAUDE.md`) →
local. More specific wins. Personal preference goes in the user file, not the
project one — a project file is a statement about the team.

## Reporting back

Lead with the rules that are being ignored and the rewrite for each, side by
side. Then what to cut, with the reason. Say how many lines it would save.

Do not rewrite the whole file unless asked. A CLAUDE.md is a team artefact, and
handing back an unrecognisable one gets the whole review rejected.
