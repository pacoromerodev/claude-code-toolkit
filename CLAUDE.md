# claude-code-toolkit

A marketplace of Claude Code plugins under `plugins/`. The review criteria are
in `CONTRIBUTING.md`; this file holds only the rules that map to a command.

## Before you commit

Run these from the repository root; each must exit 0:

```bash
claude plugin validate . && for d in plugins/*/; do claude plugin validate "$d"; done
for c in consistency stdlib_only eval_cases eval_coverage hooks names workflows course_wording; do
  python3 ".github/scripts/check_${c}.py" || break
done
python3 plugins/skill-forge/scripts/audit_skills.py plugins/*/skills
for t in plugins/*/tests/run.sh .github/scripts/tests/run.sh scripts/tests/*.sh; do bash "$t" || break; done
```

## Rules

- Hook scripts under `plugins/*/scripts` import only the standard library, and
  only what Python 3.8 has; `check_stdlib_only.py` enforces both.
- A new block or allow branch in a hook ships with a fixture in
  `tests/fixtures/` for the input it blocks and one for the input that must
  still pass.
- A version bump changes `plugin.json`, the `marketplace.json` entry and the
  plugin's `CHANGELOG.md` in the same commit.
- In `allowed-tools`, scope `Bash` to the script the skill runs, for example
  `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_x.py *)`. Never `Bash`
  alone: it pre-approves every command for the turn the skill fires.
- Paraphrase course material in English, and cite it as
  `<course>.md:<line>`. Paste no sentence from the notes;
  `check_course_wording.py` checks what it can see.
- Keep `.claude/state/` and `.claude/handoff.md` out of commits; `.gitignore`
  covers both.
