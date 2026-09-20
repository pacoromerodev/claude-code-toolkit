---
type: llm
weight: 1
---

The file has four faults, and the user's complaint — rules being ignored — is
caused by them:

1. Vague standards: "clean code", "handle errors properly", "best practices",
   "be careful", "appropriate logging". None can be checked, so none can be
   followed.
2. Emphasis on everything: a dozen markers, which means none of them signals.
3. Two prohibitions with no alternative named.
4. A broken import: `docs/architecture.md` does not exist, so it contributes
   nothing.

Score well when the response:
- Rewrites at least two vague rules into ones a reviewer could check, showing
  before and after rather than only naming the problem
- Says emphasis is a budget and that using it everywhere spends it
- Names what to do instead of each prohibition
- Catches the broken import
- Does not simply rewrite the whole file without explanation

Score badly when the response:
- Lists the problems with no rewrites
- Adds more rules
- Says the file looks fine
- Claims the import saves context — an @import is expanded inline
