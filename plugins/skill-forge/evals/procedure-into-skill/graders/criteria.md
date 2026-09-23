---
type: llm
weight: 1
---

The mechanism is settled in the question: the user asked for a skill. What is
left is writing one that works, and the part that decides whether it ever
fires is the description.

Score well when the response:
- Produces a `SKILL.md` with frontmatter, in a directory named after the
  skill, and says where that directory goes
- Writes a description that names both what it does and the situation it
  fires in, in words someone would type — adding or changing a migration,
  altering a table, a Flyway or Liquibase file — rather than restating the
  topic
- Writes the body as the rules in order, as instructions rather than prose
- Keeps `allowed-tools` read-only, or omits it. A bare `Bash`, `Write` or
  `Edit` is wrong here: the field grants without a prompt, it does not
  restrict
- Mentions how to tell whether it works: the eval cases, or what must not
  fire it

Score badly when the response:
- Writes the body and leaves the description as a restatement of the topic
  ("Database migration rules"), with no situation in it
- Grants a bare `Bash`, `Write` or `Edit` in `allowed-tools`
- Argues for a command, a hook or a CLAUDE.md rule instead of writing what
  was asked for
- Produces prose about migrations rather than a procedure
