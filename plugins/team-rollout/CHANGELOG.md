# Changelog

All notable changes to `team-rollout`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

## [0.2.2] — 2026-09-29

### Fixed
- `settings-review` said "four locations" beside a table of five; the eval
  criterion that copied it now says five too.

## [0.2.1] — 2026-09-29

### Changed
- The managed-settings template pins `claude-sonnet-5-5`, the current Sonnet,
  at the same price as `claude-sonnet-5`.

## [0.2.0] — 2026-09-29

### Added
- One case: `local-settings-committed`. Every skill in this plugin now has the
  two positive cases and one negative that CONTRIBUTING has always
  asked for.
- `plan-rollout` covers four things it was missing: the deployment objective
  that breaks ties before any setting is touched, who decides each of the five
  decisions and what they need from you, connectors — three gates, inherited
  user permissions, read before write, sign-off by whoever owns the risk — and
  the spend levers that move the bill without touching a limit.
- `check_settings.py` checks the marketplace allowlist itself: a
  `strictKnownMarketplaces` that is not an array, an entry that is not a source
  object, an unknown source type, an empty list (reported as the lockdown it
  is), the non-existent `knownMarketplaces` key, and a git marketplace
  registered with no `ref`.

### Changed
- `plan-rollout`'s decision-owners table and five other passages tracked the
  enterprise course's wording closely; they are reworded in this plugin's own
  terms, with the same content. `settings-review`, the README and the
  `rollout-order` criteria lose one stock phrase each.
- The worked example at the end of `plan-rollout` is rewritten in this
  repository's own terms; it had followed the shape of the course's own
  example too closely.
- `settings-review` describes what Claude Code actually does with a broken
  settings file: an interactive session opens with a Settings Error dialog,
  while a `-p` run skips the file with no dialog — which is how a rule stops
  applying on a build machine and still works on a laptop. A single bad entry
  is a Settings Warning and the rest of the file stays in effect, so "the file
  loaded" is not evidence that the rule did.
- The precedence list is a table, highest first, and includes
  `claude --settings`. The old line read as "most specific wins", which is not
  the order.
- Neither the skill nor the checker offers `${CLAUDE_PLUGIN_ROOT}` as a fix
  for a relative hook path in a settings file: it is set for a hook a plugin
  ships, not for one configured there.
- `settings-review` reports a literal credential first — the file is shared,
  so the key is leaked and must be rotated — then grants wider than intended.
  It now also carries what each marketplace key actually does, and which of
  them is managed-only.

### Removed
- The command files that only restated their skill with defaults attached. A
  command's description is always-on context and the skill's is what the model
  matches on, so a wrapper paid twice for one component. What the wrappers
  added is now in the skill bodies, where it applies whether the skill was
  typed or fired on its own. `/rollout-plan` and `/settings-check`; the skills
  answer to `/team-rollout:plan-rollout` and `/team-rollout:settings-review`.

### Fixed
- Both shipped templates were rejected by Claude Code's own schema, so a
  policy that read as restrictive applied nothing: `strictKnownMarketplaces`
  was a boolean where an array belongs, `knownMarketplaces` is not a setting,
  and a `$comment` sat inside `hooks`, which takes event names only. CI now
  validates every shipped settings file against the published schema.
- `not-fired` eval grader says what a correct answer looks like; it had failed
  a correct Shift+Tab answer.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.

## [0.1.0] — 2026-09-20

### Added
- `plan-rollout` skill: the five decisions in the order that stops them being
  redone — Structure and Identity, Access, Governance, Spend, Visibility —
  with the four that are hard to undo called out, the additive group rule and
  its consequence for anything regulated, and what actually happens at a spend
  limit.
- `settings-review` skill + `scripts/check_settings.py`: blanket allows,
  bypass as a default mode, literal credentials, unpinned marketplaces,
  relative hook paths, missing timeouts on blocking events, and settings files
  that cannot be parsed — which Claude Code ignores silently.
- `settings/managed-settings.json` and `settings/project-settings.json`:
  reference files with every choice commented.
- `/rollout-plan` and `/settings-check` commands.
- 22 fixture assertions, including that the shipped templates pass the
  checker this plugin ships.
