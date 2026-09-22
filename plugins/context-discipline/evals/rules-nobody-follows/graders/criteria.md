---
type: llm
weight: 1
---

Emphasis is a budget: past a handful of markers none of them signals
anything, so marking the important rules makes every rule equally loud. The
length is the actual problem, and the rules that must never be broken do not
belong in a file that only asks.

Score well when the response:
- Says adding emphasis will not work, and why: it is relative, so marking
  more rules marks none
- Goes after the length — most of a 400-line file is documentation rather
  than instruction, and it competes with the task on every turn
- Says a rule that must hold belongs in a PreToolUse hook that exits 2, not
  in this file
- Mentions position: what must hold goes first and is worth repeating last
- Offers to run the checker, or names what it would find

Score badly when the response:
- Agrees with adding IMPORTANT, or suggests capitals and bold as the fix
- Suggests splitting the file across @imports to save context, which splices
  them in whole
- Rewrites the file without addressing why it is being ignored
