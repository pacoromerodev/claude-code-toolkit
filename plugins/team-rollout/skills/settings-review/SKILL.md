---
name: settings-review
description: Reviews a Claude Code settings file for permissions that are wider than intended, unpinned plugin marketplaces, literal credentials and hooks that will not resolve. Use when writing or reviewing settings.json or a managed policy, when deciding what a team may run without prompting, or when a hook does not fire.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_settings.py *)
---

# Reviewing settings

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_settings.py .claude/settings.json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_settings.py managed.json --managed
```

`--managed` holds the file to the stricter bar a policy file needs. With
nothing named, check every settings file in the repository, and
`~/.claude/settings.json` if it exists — a rule that appears to be ignored is
usually a correct rule in the wrong one of the four locations below.

## Where a rule belongs

Highest wins, and the order is not "most specific":

| | File | Set by |
|---|---|---|
| 1 | managed settings | the organisation — cannot be overridden below |
| 2 | `claude --settings <file>` | you, for one session |
| 3 | `.claude/settings.local.json` | you, in this project (gitignored) |
| 4 | `.claude/settings.json` | everyone in the project |
| 5 | `~/.claude/settings.json` | you, everywhere |

Managed settings being un-overridable is what makes them right for the few
rules that must hold and wrong for preferences: nobody below can adjust one,
including for a good reason.

**A project file is a statement about the team.** Personal preferences go in
the user file. This is the most common misuse: someone's editor habit committed
into a repository where it now applies to everyone.

## What the checker finds, and why each matters

**A blanket allow.** `Bash` grants every command; `Bash(npm test:*)` grants
one. Broad entries get added to stop a prompt during one frustrating afternoon
and are never narrowed afterwards, because nothing prompts again to remind you.

**No deny list.** An allow list says what is permitted. A deny list holds even
when a project file widens things, which is why credentials, history files and
production config belong in it.

**An allowlist that allows everything.** Installing a plugin executes its code
as the user, and its hooks stack with everyone else's, so the list of
marketplaces people may install from is a supply-chain decision. Two keys, and
they do different jobs:

| Key | Where | What it does |
|---|---|---|
| `strictKnownMarketplaces` | managed policy only | Array of source objects. Restricts what may be added; an empty array blocks every marketplace, the official one included. |
| `extraKnownMarketplaces` | any file | Object keyed by name. Registers a marketplace so nobody adds it by hand. Restricts nothing. |

```json
"strictKnownMarketplaces": [
  { "source": "github", "repo": "your-org/your-marketplace", "ref": "v1.0.0" }
]
```

Two ways this goes wrong quietly. `strictKnownMarketplaces: true` reads as
"locked down" and is a type the schema rejects, so the whole entry is dropped
and nothing is restricted — the checker reports it as an error. And
`knownMarketplaces` is not a setting at all: nothing reads that key.

**A git marketplace with no `ref`.** Whatever the default branch holds today is
what the team installs tomorrow, hooks included. Pin a tag.

**A literal credential.** Settings files get committed, shared and synced.
Anything matching a key pattern in one should be treated as leaked and rotated.

**A relative hook path.** `./scripts/hook.sh` resolves against whatever
directory the session started in, so the hook silently does not run. In a
settings file the fix is `"$CLAUDE_PROJECT_DIR"/scripts/hook.sh`, quoted.
(`${CLAUDE_PLUGIN_ROOT}` is for a hook a plugin ships, and is not set for
one configured here.)

**A hook with no timeout** on `Stop`, `PreCompact` or `SessionStart`. Those
events can block the session, and a hook that hangs there leaves it unable to
finish.

**Invalid JSON, or a value the schema rejects.** An interactive session opens
with a Settings Error dialog — fix it with Claude's help, exit, or continue
without that file. A `-p` run shows no dialog at all: the file, or the entry,
is skipped and the run continues, which is how a rule stops applying on a
build machine while it still works on a laptop. `claude doctor` lists what was
dropped, and `/status` shows which files loaded.

**One bad entry is not one bad file.** A malformed permission rule or an
unknown hook event name is a Settings Warning: that value is skipped and the
rest of the file stays in effect. So "the file loaded" is not evidence that
the rule you care about did.

## Starting from the templates

`settings/managed-settings.json` and `settings/project-settings.json` in this
plugin are reference files with every choice commented. Copy and narrow; do not
copy and widen.

## Reporting

Lead with any literal credential: the file is shared, so the key is already
leaked — say to rotate it, not only to move it. Then anything granting more
than intended, then anything that will not work at all — a relative hook path,
unparseable JSON. Say which file each rule belongs in: a surprising number of
problems are a correct rule in the wrong one of the four locations.
