---
type: llm
weight: 1
---

A correction that repeats, on a situation the model can recognise, and the
user has ruled out typing anything. That is a skill: it fires on its own
description when a migration is being written.

Score well when the response:
- Proposes a skill rather than a command, and connects that to what the user
  said — nothing is typed, it has to fire on its own
- Treats the description as the part that decides whether it ever fires, and
  writes one that says both what it does and when: adding or changing a
  migration, altering a table, a Flyway or Liquibase file
- Writes the body as the rules, as a procedure rather than prose
- Says where the file goes — a directory named after the skill, with
  `SKILL.md` inside it
- Mentions at least one of: the negative case (what must not fire it), that
  `allowed-tools` grants rather than restricts, or auditing the result

Score badly when the response:
- Recommends a slash command, or a CLAUDE.md rule, as the main answer
- Writes the body and leaves the description as a restatement of the topic
- Suggests a hook for a rule the model has to apply while writing SQL, with
  no way to check the output
- Answers with general advice about migrations instead of setting this up
