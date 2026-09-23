---
name: write-a-skill
description: Writes a new Claude Code skill from scratch — the procedure, the frontmatter and the eval cases. Use when the user asks to write, create, scaffold or add a skill, or to turn a repeated procedure into a reusable one. For a skill that exists and does not fire, use audit-skills for what is wrong with it and skill-describer for the description.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit_skills.py *)
---

# Writing a skill

A skill is a procedure the model follows when a situation arises. It is not
documentation, and it is not a command — nobody types it. Something has to
match it, and that something is the description.

## Before writing anything

Answer these:

1. **What situation does this fire in?** In the words a user would actually
   type, not the words you would use to name the concept.
2. **What should it stop happening?** A skill that changes nothing about the
   output is a skill nobody notices is missing.
3. **What would firing it wrongly cost?** Every false positive spends context
   on an unrelated turn.

If the first two have no clear answer, what is wanted is probably not a skill:

| | Starts with | Runs in | Reach for it when |
|---|---|---|---|
| **Skill** | The model matching a description | This conversation | A situation recurs and the model should handle it the same way each time |
| **Command** | Someone typing `/name` | This conversation | The user decides when, and nothing should fire on its own |
| **Subagent** | Delegation | Its own context, returning a summary | The work is long or noisy and only the conclusion should come back |
| **Hook** | An event | A shell, deterministically | It must happen every time, whatever the model decides |

The answer is often two of them: a subagent for the work, and a skill whose
description is how the model knows to delegate to it.

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
name: verify-changes            # ≤64, lowercase, hyphens; match the directory
description: Verify that a ...  # what it does AND when to use it
allowed-tools: Read, Grep       # optional: pre-approved, see below
model: inherit                  # optional: haiku | sonnet | opus | inherit
---
```

Every field is optional, and the one that matters is `description`: it is what
the model matches a prompt against, and a skill without one is a skill that
fires by luck. Only the name and description load at startup; the rest of the
file is read after the skill fires.

**What `name` does depends on where the skill lives.** In a plugin it becomes
the last segment of the command, `/<plugin>:<name>`. In a personal or project
skill it is only the label in the listing — the command comes from the
directory. Keeping the two identical means never having to remember which
case you are in.

**The listing truncates at 1,536 characters** of description. Past that the
text is not read by the model deciding whether to fire the skill, so the
trigger goes first, not last.

`allowed-tools` **grants**; it does not restrict. Every tool listed runs
without a permission prompt on the turn the skill fires, and tools not listed
stay available through the normal prompt. So list read tools freely. List
`Bash` only scoped to the script the skill runs, written exactly as the body
invokes it:

```yaml
allowed-tools: Read, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check.py *)
```

A bare `Bash` lets any command run unprompted whenever the skill matches a
prompt. Leave `Write` and `Edit` out: file changes should go through the
user's normal permission flow. The auditor reports both.

## Skills and subagents

They compose, in both directions:

- A subagent can be given a `skills:` list, which preloads those skills into
  its startup context. Use it when the subagent's whole job depends on a
  procedure, rather than hoping its description matches.
- A skill can hand its own work to a subagent with `context: fork` and an
  `agent:` to run it. The skill body becomes the task, and only the summary
  comes back — worth it when the procedure reads a lot and the conversation
  needs none of it.

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
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit_skills.py <skills-dir>
```

Then write the eval cases — at least three:

- Two prompts that **should** fire it, worded differently from the description
  and from each other
- One prompt in the same domain that should **not**

The negative case is not optional. A skill that fires on everything costs
context on every unrelated turn, and nothing in the audit can detect that.

## When a skill does not fire

Check in this order. It is almost always the first one.

1. **The description.** Does it name the situation in the user's words?
   **Delegate this one.** Rewriting a description from the body is not a
   one-shot edit: it needs candidates that differ in coverage, each with the
   prompts it would catch and the prompts it would wrongly catch. Launch the
   `skill-describer` subagent with the body and the skills it sits beside, and
   use what comes back. Writing a single replacement yourself is the failure
   this skill exists to prevent — it reads better and matches the same nothing.
2. **The name and the directory** — do they match exactly?
3. **Is `SKILL.md` inside a directory of that name**, not loose?
4. **Does another skill's description overlap?** When both match, which fires
   is arbitrary.
5. **Is it a subagent that needs it?** Subagents do not inherit skills; list it
   in their `skills:` field. The built-in Explore, Plan and Verify agents cannot
   use skills at all.
6. `claude --debug` shows what loaded.
