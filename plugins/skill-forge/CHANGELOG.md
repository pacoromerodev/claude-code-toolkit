# Changelog

All notable changes to `skill-forge`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

## [0.2.1] — 2026-09-29

### Fixed
- `audit_skills.py` asked a skill with `disable-model-invocation: true` to say
  when to use it, and counted its description in the overlap check. No prompt
  is matched against such a skill: its description is the line in the `/`
  menu. Both rules now skip it, and a skill the model may invoke is held to
  them as before.

## [0.2.0] — 2026-09-25

### Removed
- `write-a-skill`, the `audit-skills` skill and the `skill-describer`
  subagent, with their eval cases. Across all six cases, run three times each
  against a no-plugin baseline, every one scored 1.00 against 1.00: the model
  writes, audits and rewrites skill descriptions as well without them, and
  in four runs of `description-rewrite` it never delegated to the subagent.
  The auditor script and the routing log stay; neither is something an eval
  of a conversation can measure.
- The `/audit-skills` and `/new-skill` commands. `/audit-skills` had the same
  name as the skill, and in an installed plugin the command won, so the
  skill's procedure never loaded.

### Added
- Routing telemetry, opt-in per project with `.claude/routing-log`. A
  `UserPromptSubmit` hook records the prompt and a `PreToolUse` hook on
  `Skill|Task` records what fired; `routing_report.py` reports what fires, how
  often, and which prompts fired nothing. That last list is the half an eval
  cannot see: a case measures a prompt written for it, this measures the
  prompt someone typed. The log lives outside the repository, the prompt is
  truncated, and nothing is sent anywhere.
- `audit_skills.py` audits subagents. Pointed at a plugin's `skills/` it also
  reads the `agents/` beside it, and reports: a reviewing agent granted
  `Write` or `Edit`, an output format with no section for what the agent could
  not check, a persona line, a description that never says when to delegate,
  and one that never says what to pass — the description shapes the delegation
  prompt, so asking for the files is how the main thread comes to send them.
  The agents this repository ships now say what to pass, which is how that
  last rule was found.

### Fixed
- The routing log saw no delegation to a subagent. Its `PreToolUse` matcher
  named `Task`, and current Claude Code calls the tool `Agent`; the matcher
  now names both. A test now checks the matcher itself: the existing ones fed
  the script directly and could not see it.
- `audit_skills.py` warned that `allowed-tools: Agent` names an unknown tool.
- `audit_skills.py` treated a skills root holding a loose `SKILL.md` as a
  single skill: it audited only that file, misreported it as a name mismatch,
  and never looked at the real skills beside it. The loose file is now an
  error of its own and the rest of the root is audited.

## [0.1.0] — 2026-09-20

### Added
- `write-a-skill` skill: scaffolds a skill correctly and, more importantly,
  spends its length on the description — the only field loaded at startup and
  the reason most skills never fire.
- `audit-skills` skill wrapping `scripts/audit_skills.py`: finds name/directory
  mismatches, missing or unclosed frontmatter, missing descriptions,
  descriptions with no trigger, oversized bodies, misplaced `SKILL.md` files,
  non-executable scripts, unreferenced `references/` files, and descriptions
  that overlap each other.
- `skill-describer` subagent: writes three candidate descriptions that differ
  in coverage — narrow, broad, balanced — and names what each would and would
  not match, including likely false positives.
- `/new-skill` and `/audit-skills` commands.
- 15 fixture assertions over a tree with planted faults and a clean tree; the
  suite also audits this repository's own skills.
