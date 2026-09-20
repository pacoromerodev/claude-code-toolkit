---
name: write-a-skill
description: Create a new Claude Code skill, or fix one that never fires. Use when the user asks to write, create, scaffold or add a skill, when they want to turn a repeated procedure into a reusable one, or when an existing skill is not triggering and the description needs rewriting.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Writing a skill

A skill is a procedure the model follows when a situation arises. It is not
documentation, and it is not a command — nobody types it. Something has to
match it, and that something is the description.

## Before writing anything

Answer these. If the first two have no clear answer, the thing being asked for
is probably a command or a subagent, not a skill — check `docs/anatomy.md`.

1. **What situation does this fire in?** In the words a user would actually
   type, not the words you would use to name the concept.
2. **What should it stop happening?** A skill that changes nothing about the
   output is a skill nobody notices is missing.
3. **What would firing it wrongly cost?** Every false positive spends context
   on an unrelated turn.

## Layout

```
<skill-name>/
├── SKILL.md            # name, description, body under 500 lines
├── references/         # long material, loaded only when the body points at it
├── scripts/            # executed without being read into context
└── assets/             # templates, files the skill copies
```

The directory name and the `name` field must match exactly, and `SKILL.md` must
sit inside that directory. A file loose in the skills root silently never loads.

## Frontmatter

```yaml
---
name: verify-changes            # ≤64, lowercase, hyphens, == directory name
description: Verify that a ...  # ≤1024, what it does AND when to use it
allowed-tools: Read, Bash       # optional: narrows what it may use
model: inherit                  # optional: haiku | sonnet | opus | inherit
---
```

Only `name` and `description` are required, and only those two load at startup.
Everything else in the file is read after the skill fires.

## The description is the skill

This is where skills fail, and where you should spend your effort.

At startup the model sees only the name and the description. Whether the skill
ever runs is a semantic match against that one field. The body can be perfect
and it will never be read.

A description answers two questions:

- **What does it do?** One clause.
- **When is it used?** The rest — and this is the part people leave out.

Write triggers in user language:

| Weak | Why | Better |
|---|---|---|
| "Helps with database migrations." | Says what it is about, never when to use it. | "Reviews a Flyway or Liquibase changeset before it is applied. Use when the user adds or edits a migration, asks whether a migration is safe, or is about to deploy a schema change." |
| "This skill provides code review capabilities." | Opens with "this skill", spends characters on nothing. | "Reviews uncommitted changes and reports findings by severity. Use before a commit or a pull request, or when the user asks for a review or a second opinion." |
| "For testing." | Nothing can match this. | "Runs the project's test suite and checks that no test was weakened to make it pass. Use after implementing a change, before committing." |

Name the situation the user is in, not the abstraction you have in mind.

## Body

Under 500 lines. Write it as a procedure with steps the model can follow and
you can check it followed. Tables for decisions, commands in fenced blocks,
explicit output format if the skill produces a report.

Push everything heavy out of it:

- **`references/`** — long tables, API details, worked examples. Mention the
  filename in the body, or it never loads.
- **`scripts/`** — anything executable. Scripts run without being read into
  context, which is how a skill carries a thousand lines of logic for the price
  of a description. Make them executable: `chmod +x`.

## Requiring evidence

If the skill produces a report, define the shape in the body, and include a
section for what it could not check. A report without that section reads as
complete whether or not it is.

## Before calling it done

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit_skills.py" <skills-dir>
```

Then write the eval cases — at least three:

- Two prompts that **should** fire it, worded differently from the description
  and from each other
- One prompt in the same domain that should **not**

The negative case is not optional. A skill that fires on everything costs
context on every unrelated turn, and nothing in the audit can detect that.

## When a skill does not fire

Check in this order. It is almost always the first one.

1. **The description.** Does it name the situation in the user's words? Try
   `skill-describer` for three alternatives and what each would match.
2. **The name and the directory** — do they match exactly?
3. **Is `SKILL.md` inside a directory of that name**, not loose?
4. **Does another skill's description overlap?** When both match, which fires
   is arbitrary.
5. **Is it a subagent that needs it?** Subagents do not inherit skills; list it
   in their `skills:` field. The built-in Explore, Plan and Verify agents cannot
   use skills at all.
6. `claude --debug` shows what loaded.
