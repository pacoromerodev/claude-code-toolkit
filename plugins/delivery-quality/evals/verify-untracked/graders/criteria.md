---
type: llm
weight: 1
---

`src/tax.py` and `tests/test_tax.py` were never added to git, so `git diff
HEAD` is empty. A verification that stops there reports a clean change and has
read nothing.

The files themselves have two real problems: `test_spain` asserts only that
the result is not None, which passes for any number including a wrong one, and
`test_unknown_country` asserts nothing at all. An unknown country silently
being charged no tax is worth raising as well.

Score well when the response:
- Reads the untracked files — by listing them (`git status`, `git ls-files
  --others`) or by reading the paths directly — rather than concluding there
  is nothing to review
- Says that `git diff` shows nothing because the files are untracked, if it
  mentions the diff at all
- Flags `test_spain` as an assertion that cannot fail meaningfully, and
  `test_unknown_country` as having no assertion
- Keeps the report's shape, including what it could not check

Score badly when the response:
- Reports the change as verified, or reports that there is nothing to review
- Runs the tests, sees them pass, and treats that as evidence
- Reviews only `README.md`, the one tracked file
