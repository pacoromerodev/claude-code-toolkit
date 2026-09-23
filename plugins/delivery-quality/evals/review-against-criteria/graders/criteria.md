---
type: llm
weight: 1
---

TASK.md states four acceptance criteria. The change meets three — active rows
only, the column order, the date format — and each has a test. The fourth,
writing an export of more than 10,000 rows in batches so memory does not grow,
was never implemented: `write_csv` builds the whole list in memory first.

The tests pass, and they were written from the same reading of the task, so
they cover the same three.

Score well when the response:
- Reads TASK.md and checks the change against the criteria by name
- Reports the batching criterion as not implemented, pointing at the list
  comprehension that materialises every row
- Says the suite passing is not evidence for it, because no test covers it
- Confirms the three that are met rather than leaving them unstated
- Keeps its own gaps section

Score badly when the response:
- Reviews style, naming or error handling without checking the criteria
- Reports the change as complete, or as matching the task
- Mentions memory only as a general performance remark, unconnected to the
  stated criterion
