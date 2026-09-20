---
type: llm
weight: 1
---

The migration does two unsafe things:

1. Drops `orders.legacy_reference`, which `OrderRepository.findLegacyReference`
   still queries. During a rolling deploy the previous version keeps running and
   its query fails.
2. `CREATE INDEX` without `CONCURRENTLY`, which locks writes on `orders` for the
   duration of the build.

Score well when the response:
- Reports the dropped column as blocking, and connects it to the code that
  still reads it — ideally naming the repository method
- Describes the failure in rolling-deploy terms: the old version is still
  serving traffic against the new schema
- Gives the expand/contract split — stop reading it, ship, drop it next release
- Also catches the non-concurrent index
- Says what it could not check, such as the size of the table

Score badly when the response:
- Calls the migration safe
- Reports only the index and misses the dropped column
- Reports the drop as a style issue rather than something that breaks the deploy
- Suggests simply running it during a maintenance window without saying that
  the code still reads the column
