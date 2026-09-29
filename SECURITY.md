# Security

## What is in scope

The plugins here run code on the machine of whoever installs them, with that
person's privileges. The parts that matter for security are the hooks:

| Plugin | Hook | Runs on |
|---|---|---|
| delivery-quality | `guard_secrets.py` | every `Write`, `Edit`, `NotebookEdit`, `Bash` and `PowerShell` call |
| delivery-quality | `guard_destructive.py` | every `Bash` call |
| delivery-quality | `test_gate.py` | session stop, only in a project that opted in |
| regulated-delivery | `guard_pii.py` | every `Write`, `Edit`, `MultiEdit` and `NotebookEdit` call |
| context-discipline | `save_state.py`, `restore_state.py` | compaction, and the session that resumes after it |
| skill-forge | `log_routing.py` | every prompt and every `Skill`, `Task` and `Agent` call; writes nothing unless enabled |

Worth reporting:

- **A way past a guard.** A command that destroys work, or a write that puts
  a real credential or a real account, card or national ID on disk, which
  the matching guard lets through. Give the
  exact tool input.
- **A hook that does something it does not say.** Network access, a write
  outside the project or the state directory, text injected into the context
  that did not come from the project.
- **A skill whose `allowed-tools` pre-approves more than it runs.**
  `CLAUDE.md` sets the rule.

## What the guards are not

They are guardrails for a cooperating model, not a sandbox. They match known
shapes of dangerous input, and every one fails open: a guard that crashes
lets the call through rather than locking the session (see
[CONTRIBUTING.md](CONTRIBUTING.md), *Hooks fail open*). A bypass is still a
bug worth fixing, but do not rely on these hooks as the only barrier between
an untrusted prompt and your machine. Use Claude Code's permission modes and
sandboxing for that.

## Known and fixed

[AUDIT.md](docs/history/AUDIT.md) documents guard bypasses (C2) and a context-injection
path (H1) found in the second audit. All of them were fixed in Phase 9 of
[ROADMAP-v2.md](docs/history/ROADMAP-v2.md), whose status table records re-running the
audit's probe against them. Blocking branches carry fixtures in the plugin's
`tests/fixtures/`, one input that must be blocked and one that must pass, and
CI runs them on Python 3.8 and 3.12.

## Reporting

Report privately through GitHub: **Security → Report a vulnerability** on
this repository. Do not open a public issue for a working bypass. The issue form links
there as well.

Include the plugin and its version (from `/plugin` or the plugin's
`.claude-plugin/plugin.json`), your Claude Code version, the tool input or
command, and what happened. A fix comes with a fixture for the input, so the
same bypass cannot return unnoticed.
