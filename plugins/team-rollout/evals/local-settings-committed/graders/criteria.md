---
type: llm
weight: 1
---

A project file is a statement about the team, and a personal allow-list is
the most common thing to find in the wrong one of the four locations. The fix
is placement plus a deny list, which holds even when someone widens things
below it.

Score well when the response:
- Says the personal entries belong in the user file, or in
  `.claude/settings.local.json`, which is gitignored
- Says what the project file is for: what everyone in the project needs, the
  hooks the project runs, the denials that must hold
- Recommends a deny list for credentials, history files and production
  config, and says it survives a widening below it
- Mentions that the thirty Bash entries are worth narrowing rather than
  moving wholesale — a blanket grant never gets narrowed once nobody is
  prompted

Score badly when the response:
- Only says to revert the commit
- Recommends putting the entries in the managed policy
- Answers with the precedence order and nothing about which rule belongs
  where
