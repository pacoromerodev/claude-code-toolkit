---
type: llm
weight: 1
---

This is a skill: a procedure that recurs, with a situation that can be
described in the words someone would use. The work is deciding what fires it
and writing the body as a procedure — not writing a document about releases.

Score well when the response:
- Proposes a skill, and says what makes it one: a recurring procedure with a
  recognisable trigger
- Writes a description that says both what it does and when it fires, in the
  words someone would type ("cut a release", "ship a version")
- Writes the body as the six steps in order, as instructions rather than
  prose
- Covers the frontmatter honestly: the description is what matters; any
  `Bash` grant is scoped to the command it runs, not bare
- Mentions the negative case — what should not fire it — or the eval cases

Score badly when the response:
- Suggests a slash command as the only option, with no mention of a skill
  firing on its own
- Produces a document about the release process rather than a procedure
- Grants a bare `Bash` in `allowed-tools`
- Writes a description that only names the topic, with no trigger
