---
name: audit-skills
description: Check a directory of skills for the faults that stop them firing — a name that does not match its directory, a description that never says when to use the skill, a SKILL.md in the wrong place, overlapping descriptions, oversized bodies, unreferenced files. Use when a skill is not triggering, before sharing or publishing skills, or when the user asks to review, audit or check their skills.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit_skills.py *)
---

# Auditing skills

Most "my skill doesn't work" reports are one of a handful of faults. This
checks for all of them mechanically, so you spend your attention on the one
that needs judgement: the description.

## Run it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit_skills.py <path>
```

Point it at a directory of skill directories (`.claude/skills`,
`~/.claude/skills`, `plugins/*/skills`) or at one skill. Add `--json` when you
need to process the result rather than read it.

Exit 1 means at least one error. Warnings alone exit 0 — they are judgement
calls, not violations.

## What the errors mean

| Error | Effect |
|---|---|
| `name` does not match the directory | The skill does not resolve. It is simply absent. |
| No `SKILL.md` in a skill-looking directory | Silently never loads. No warning anywhere. |
| No frontmatter, or it is never closed | Never loads: name and description are all that is read at startup. |
| No `description` | Nothing can ever match it. |
| `name` over 64 or `description` over 1024 | Rejected. |
| Body over 500 lines | Too big to stay coherent. Move material to `references/`. |

## What the warnings mean

**"description never says when to use the skill"** is the one worth acting on.
It means the description reads as a definition — what the skill *is* — with no
trigger. The model matches prompts against this field and nothing else at
startup, so a description without a situation in it is a skill that fires by
luck.

**"description overlaps N% with X"** means two skills match the same prompts.
Which one fires is then arbitrary, and the fix is to make each name the
situation the other does not cover.

**"references/x.md is never mentioned"** means a file that never loads. Either
point at it from the body or delete it.

**"scripts/x.sh is not executable"** means it cannot be run directly.

## Reporting back

Lead with the errors — those are breakage, not opinion. Then the warnings,
grouped by skill, with the fix rather than the restatement.

If the audit is clean but the skill still does not fire, the problem is the
description's wording, not its structure. Hand it to `skill-describer` for
alternatives.
