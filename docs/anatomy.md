# Which component do I reach for?

Claude Code offers five ways to extend it, and they fail in different ways when
you pick the wrong one. This is the decision, written once so plugin READMEs
can link here instead of repeating it.

## The five

| | Loaded | Triggered by | Costs context |
|---|---|---|---|
| **CLAUDE.md** | Every session, always | Nothing — it is simply present | Always, in full |
| **Skill** | Name and description at startup; body on demand | Semantic match against the description | Only when it fires |
| **Command** | On demand | You typing `/name` | Only when run |
| **Subagent** | Its own separate context | The main thread delegating | Only its summary comes back |
| **Hook** | Never — it is code | An event, deterministically | Nothing |

## Choosing

**Does it need to be true every time?** CLAUDE.md. But it is guidance, not
configuration: it is read, not executed, and everything in it competes for
attention. The longer it gets, the less of it survives. Keep rules specific
and checkable, name the alternative rather than only the prohibition, and spend
emphasis like a budget — if everything is important, nothing is.

**Must it happen, without the model choosing?** A hook. Hooks are the only
deterministic extension: they run on the event, every time, whatever the model
decided. Formatting on save, blocking a write, gating a session on tests.

**Is it a procedure the model should follow when a situation arises?** A skill.
The description decides whether it fires, which makes the description the
component — not the body. Write it to answer both *what this does* and *when to
use it*, and test that with evals, including a case where it must stay quiet.

**Do you want to run it explicitly, on demand?** A command. The cost is that
you have to remember it exists. A skill is found for you; a command is typed.

**Is the intermediate work something you need to see?** If yes, keep it in the
main thread. If no — you want the conclusion, not the forty files it read to
reach it — a subagent. That is the whole decision rule.

## Subagents, specifically

A subagent gets a fresh context and returns only a summary. That is the benefit
and the cost in one sentence: the main thread is spared the noise, and loses
the ability to see what happened.

Which makes the output format the design decision. Fixed headings create a stop
point where the work becomes checkable. A required section for gaps —
"Obstacles encountered" — is the only way an unfinished check reaches the
person reading the summary.

**Antipatterns, in order of how often they look reasonable:**

- **Persona agents.** "You are a senior security architect" buys nothing over
  stating the task, the allowed tools and the output shape.
- **Sequential pipelines.** Agent A hands to B hands to C. Each handoff is a
  lossy summary, and by C the original detail is gone. Orchestrate from the
  main thread instead.
- **Test runners.** Delegating a test run is the worst measured configuration:
  you lose the output, keep the latency, and gain a summary of failures you
  now have to re-derive.

## Skills, specifically

Only the name and description load at startup. The body loads when the skill
fires, and files under `references/` load only when the body points at them.
Scripts under `scripts/` are executed without being read into context at all —
which is how a skill can carry a thousand lines of logic for the price of a
description.

Precedence when names collide: **Enterprise → Personal → Project → Plugins.**

**Subagents do not inherit skills.** A subagent that needs one has to list it
in `skills:`. The built-in Explore, Plan and Verify agents cannot use skills at
all.

When a skill does not fire, the description is almost always why. Before
touching the body, check: does it name the situation in the words a user would
actually use, or only the words the author would?

## Hooks, specifically

Events worth knowing: `PreToolUse` and `PostToolUse`, `UserPromptSubmit`,
`Stop`, `SessionStart`, `PreCompact`, `Notification`.

The exit-code contract is narrow and easy to get wrong:

| Exit | Meaning |
|---|---|
| 0 | Continue |
| **2** | **Block, and hand stderr to Claude as feedback** |
| anything else | Non-blocking — including 1 |

Exit 2 is what makes a hook useful rather than merely noisy: the model sees the
reason and corrects itself, instead of retrying the same call.

For richer control a `PreToolUse` hook can return JSON with a
`permissionDecision` of `allow`, `deny`, `ask` or `defer`, and an
`updatedInput` that **replaces the input object entirely** — which is how you
redact a value rather than reject the call.

To restore state after compaction, use `SessionStart` with the matcher
`compact`. That is the event carrying the resumed session; `PostCompact` is not
where the reinjection belongs.

`${CLAUDE_PLUGIN_ROOT}` resolves to the installed plugin directory.
`CLAUDE_PROJECT_DIR` is the project root. Use both; never a relative path.

## Plugins

A plugin is the installable unit: skills, subagents, commands, hooks and MCP
servers in one directory, distributed through a marketplace.

**A plugin runs code with your privileges, and its hooks stack with everyone
else's.** Read one before installing it. For an organisation, run a private
marketplace and pin it with `strictKnownMarketplaces` rather than trusting
whatever a developer adds.

In `settings.json`, a plugin may only set `agent` and the subagent status line.
The `agent` key promotes a subagent to the main thread.

The manifest, `.claude-plugin/plugin.json`, requires only `name` — but a plugin
that ships without a description is a plugin nobody installs.
