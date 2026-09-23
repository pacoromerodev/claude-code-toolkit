---
type: llm
weight: 1
---

Being able to turn it on is not the question. Three things decide this: the
connector passes three gates before anyone can use it, write depth is a
different decision from read, and a team handling payments is the one case
where a general group grant cannot be narrowed afterwards.

Score well when the response:
- Names the three gates — the organisation, the group's role, and each
  person's own account connection — and that all three must be open
- Separates read from write, and recommends starting read-only unless the
  workflow demonstrably needs write
- Says write access should be signed off by whoever owns the data risk, not
  by the requesting team or the admin who can flip the switch
- Points out that Claude acts with that user's own permissions in Drive, so
  the blast radius is whatever each member can already reach
- Raises that a regulated team needs its own group, because group membership
  is additive and a broad grant cannot be taken back by a narrow one
- Mentions announcing it, and that withdrawing later breaks a workflow people
  will have built on

Score badly when the response:
- Explains how to enable it and stops
- Treats write access as an ordinary configuration change
- Recommends granting it to a general group that the payments team sits in
- Says Claude's access can be restricted below what the user already has in
  the connected system
