# java-spring

Backend conventions for Java and Spring Boot, written so they hold at any
company.

```
/plugin install java-spring@pacoromerodev
```

Where a project's own conventions differ, the project wins — every skill says
so, and says to read the existing code first.

## Components

| Component | Type | Fires when |
|---|---|---|
| `spring-boot-service` | Skill | Adding an endpoint, service or repository; wiring configuration; deciding a transaction boundary |
| `kafka-consumer` | Skill | Adding or changing a listener; messages reprocessed or lost; a stuck partition; retry and DLT setup |
| `java-21-modernize` | Skill | Modernising older Java; deciding on a record, sealed type or virtual threads |
| `test-shape` | Skill | Adding tests; deciding what to mock; a test that breaks on every refactor |
| `migration-review` | Subagent | A Flyway or Liquibase file changes, or before a release carrying a schema change |
| `/review-migration` | Command | Typed, to launch the subagent |

## The migration reviewer

The question it asks is not whether the SQL is valid — it will be. It is what
happens when the migration runs **while the previous version of the application
is still serving traffic**. During a rolling deploy both versions share one
schema, and that is what makes a migration unsafe.

The mechanical pass runs as a script:

```bash
python3 plugins/java-spring/scripts/check_migration.py src/main/resources/db/migration
```

| Caught | Why it breaks a deploy |
|---|---|
| `CREATE INDEX` without `CONCURRENTLY` | Exclusive lock on writes for the whole build |
| `NOT NULL` with no default | Fails outright on any existing row |
| `SET NOT NULL` | Full table scan, and fails if any row is null |
| `DROP` / `RENAME COLUMN`, `DROP TABLE` | The running version is still reading it. A rename is a drop and an add |
| `UPDATE` / `DELETE` with no `WHERE` | Locks every row for as long as the table is big |
| Type changes | Rewrites the table, can truncate |
| Duplicate Flyway version | Flyway refuses to start |
| Foreign key validated inline | Full scan under a lock. `NOT VALID` then `VALIDATE` instead |
| Liquibase changeset with no rollback | Nothing to run when it goes wrong |

Then the subagent does what a script cannot: greps for the callers of a dropped
column, weighs the table size, checks the rollback actually restores data rather
than structure, and states the **deploy order** — whether the code ships first,
the migration ships first, or the two must be split across releases.

### Expand and contract

| | Release N | Release N+1 |
|---|---|---|
| Drop a column | Stop reading it, deploy | Drop it |
| Rename a column | Add the new one, write to both, backfill | Drop the old one |
| Narrow a type | Add a column, migrate, swap reads | Drop the old one |
| Add `NOT NULL` | Add nullable, backfill in batches | Add the constraint |

## Notable positions

**Kafka delivery is at-least-once, and everything follows from it.** The
`kafka-consumer` skill starts there rather than at style: a message *will*
arrive twice, on every rebalance and every redeploy, so a handler that is not
idempotent is a handler that corrupts data. Auto-commit is the quiet version of
the same failure — it acknowledges records the handler never finished, and
nothing errors.

**Virtual threads get a list of five reasons not to use them.** Pinning on
`synchronized`, a JDBC pool that is still the real limit, CPU-bound work, per-
thread caching that stops amortising, and pooling them at all. They are a change
to make with a measurement in front of you.

**No test may be weakened to go green.** `test-shape` names the specific moves —
deleting a test, `@Disabled` without a ticket, an exact assertion becoming
`notNull`, a widened range, a raised timeout — and says that if a test is
genuinely wrong, that must be stated, not quietly edited in the same commit as
the implementation.

## Tests

```bash
plugins/java-spring/tests/run.sh
```

18 assertions. Half of them check that the **safe** fixtures produce nothing: a
new table, a nullable defaulted column, a concurrent index. A checker that flags
safe migrations gets switched off, which is the same as not having one.

## Evals

```bash
claude plugin eval plugins/java-spring --scaffold --allow-tools Bash
```

- **migration-unsafe** — a migration dropping a column a checked-in repository
  still queries. The review must connect the two and give the split.
- **kafka-redelivery** — customers charged twice, with auto-commit on and a
  non-idempotent handler. The answer must start from at-least-once delivery,
  not from hunting a logic bug.
- **not-fired** — a language question about checked exceptions, which must not
  trigger a convention review.

## Requirements

Python 3.8+ on `PATH`. Standard library only. The skills assume Spring Boot 3
and Java 17 or later, and check the project's target before suggesting anything.
