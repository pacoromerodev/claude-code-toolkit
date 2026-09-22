# Changelog

All notable changes to `mcp-builder`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Removed
- The command files that only restated their skill with defaults attached. A
  command's description is always-on context and the skill's is what the model
  matches on, so a wrapper paid twice for one component. What the wrappers
  added is now in the skill bodies, where it applies whether the skill was
  typed or fired on its own. `/mcp-new`; the skill answers to `/mcp-
  builder:mcp-server-scaffold`. `/mcp-review` stays, because it launches the
  subagent.

### Fixed
- `not-fired` eval grader states what a correct answer looks like, not only
  what scores badly.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.

## [0.1.0] — 2026-09-20

### Added
- `mcp-server-scaffold` skill: picks the primitive by who is in control —
  tools for the model, resources for the application, prompts for the user —
  then writes descriptions that draw the boundary against neighbouring tools.
  Protocol detail lives in `references/protocol.md`, loaded on demand.
- `choose-transport` skill: stdio, StreamableHTTP and stateless HTTP as a
  table of what each one gives up, with the grep that finds what would break
  before switching to stateless.
- `mcp-roots-check` skill: roots are reported by the SDK and enforced by
  nobody, so this implements the check — resolve first, compare resolved to
  resolved, use the returned path.
- `mcp-review` subagent: reads each tool as the model does, name and
  description only, and returns rewritten descriptions rather than advice to
  write them.
- `scripts/check_mcp_server.py`: parses with `ast` and finds missing and thin
  descriptions, descriptions with no selection cue, untyped and vaguely named
  parameters, unbounded results, missing progress on long work, credentials
  as parameters, credentials in resource URIs, filesystem access with no path
  check, and stateless mode used alongside features it silently disables.
- `/mcp-new` and `/mcp-review` commands.
- 21 fixture assertions over a server with planted faults and one that gets
  the shape right.
