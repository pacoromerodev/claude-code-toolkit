---
name: test-shape
description: Decides what to test at which level and how to write the test so it asserts behaviour rather than implementation. Use when adding tests, when the user asks what to test or whether to mock something, when a test breaks on every refactor, or when reviewing a change that has no test.
allowed-tools: Read, Glob, Grep
---

# What to test, and where

## Choosing the level

| Level | Use for | Spring context |
|---|---|---|
| Plain unit test | Business rules, calculations, mapping, validation | None — construct the class |
| Slice (`@WebMvcTest`, `@DataJpaTest`) | Serialisation, status codes, the query itself | Partial |
| Integration (`@SpringBootTest` + Testcontainers) | Wiring, transactions, real SQL, real broker | Full |

Push work down. A rule that needs no Spring context should be a plain unit test
— it runs in milliseconds, and it is the difference between a suite you run on
every save and one you avoid.

Push *verification* up. The transaction rolled back, the index is used, the
consumer survived a rebalance: none of that is observable with mocks.

## The mock rule

**Mock what you own and control; use the real thing for infrastructure.**

Testcontainers for the database, the broker, the cache. An H2 standing in for
Postgres will happily accept SQL that production rejects, and will not reproduce
a single locking behaviour.

Mock the HTTP client you wrote, not the database.

A test with six mocks is not testing behaviour — it is asserting the order in
which the implementation calls things, which is why it breaks on every
refactor. When mocks pile up, the design is usually telling you the class has
too many collaborators.

## Assert behaviour, not implementation

```java
// asserts the implementation: breaks when the method is renamed
verify(repository).findByCustomerIdAndStatus(id, ACTIVE);

// asserts the behaviour: survives any refactor that keeps it true
assertThat(service.activeFor(id)).containsExactly(subscription);
```

If a test needs editing because the code was reorganised without changing what
it does, the test was asserting the wrong thing.

## What a test is named after

The behaviour, not the method: `refusesDiscountAboveConfiguredMaximum`, not
`testApplyDiscount2`. When it fails in CI at seven in the morning, the name is
all you have.

## Coverage that matters

For every new behaviour:

- The happy path
- **The boundary** — zero, empty, the maximum, one over the maximum
- **The failure path** — what happens when the dependency is down, the input is
  invalid, the record is missing

The failure path is the one that gets skipped, and the one that matters at
three in the morning.

## Never do this to make a suite pass

- Delete a test, or empty its body
- Add `@Disabled` without a linked ticket and a date
- Loosen an assertion: an exact value becoming `notNull`, a value becoming
  `any()`, a range widened
- Raise a timeout to hide a flaky test — find out what makes it flaky

If a test is genuinely wrong, say so explicitly and explain why the new
expectation is the correct one. Changing an expected value quietly, in the same
commit as the implementation, is how a broken change ships green.

## What to check before calling it done

- New behaviour has a test, including its failure path
- No test asserts call order unless order is the behaviour
- Infrastructure is real, not H2 or a mocked broker
- No assertion was weakened in this diff
