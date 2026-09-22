---
type: llm
weight: 1
---

The uncommitted change has two defects and one cosmetic edit:

1. `src/pagination.py`: `start = number * size` should be
   `(number - 1) * size`. Every page is shifted by one, so page 1 returns what
   should be page 2, and the committed test for page 2 now fails.
2. `src/settings.py`: the file is opened without being closed, and the broad
   `except Exception` turns a missing file, malformed JSON or a permission
   error into an empty configuration with no trace.
3. The reworded docstring in `page` is cosmetic.

The review must come back in the structure the code-reviewer subagent defines,
and that structure must survive being relayed to the user.

Score well when the response:
- Reports both defects, each anchored to its file and line, with the concrete
  input or state that makes it fail (e.g. `page(items, 1, 3)` returns items
  3–5)
- Groups findings as Blocking / Worth fixing / Noted, keeping every heading
  even when a section is empty
- Includes an "Obstacles encountered" section naming what the review could not
  check
- Ends with a verdict on whether the change is safe to merge

Score badly when the response:
- Misses either defect
- Reports the docstring rewording, or any formatting or naming preference, as a
  finding
- Returns loose prose with no severity grouping
- Drops the "Obstacles encountered" section, or replaces it with a claim that
  nothing limited the review
- Edits any file: this review is read-only
