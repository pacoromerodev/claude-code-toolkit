---
type: llm
weight: 1
---

Three faults, of different severity:

1. A literal API key in `env`. This file is about to be shared with a team, so
   the key must be treated as leaked and rotated — the most urgent item.
2. `allow: ["Bash", "Write", "Read(*)"]` grants entire tools rather than
   patterns, to everyone on the team.
3. The hook command `./scripts/format.sh` is a relative path, which resolves
   against whatever directory the session started in. The hook silently never
   runs.

Score well when the response:
- Finds all three
- Treats the credential as the urgent one, and says it should be rotated rather
  than merely moved
- Replaces the blanket permissions with narrowed patterns, showing them
- Explains that the relative hook path fails **silently**, and gives
  `$CLAUDE_PROJECT_DIR` as the fix
- Notes there is no deny list, for a file being rolled out to a team

Score badly when the response:
- Misses the credential, or only says "move it to an environment variable"
  without saying to rotate it
- Calls the permissions acceptable
- Reports the hook path as a style issue rather than something that does not run
