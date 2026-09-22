# Changelog

All notable changes to `java-spring`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

### Added
- Six cases: `records-or-lombok`, `out-of-order-updates`,
  `transaction-boundary`, `what-to-test`, `legacy-date-parsing`,
  `config-in-service` and `flaky-time-test`. Every skill in this plugin now has the
  two positive cases and one negative that CONTRIBUTING has always
  asked for.

### Changed
- `test-shape` names Java, Spring Boot and JUnit. Without them it matched any
  testing question in any language, which is not what it knows about.

### Removed
- The command files that only restated their skill with defaults attached. A
  command's description is always-on context and the skill's is what the model
  matches on, so a wrapper paid twice for one component. What the wrappers
  added is now in the skill bodies, where it applies whether the skill was
  typed or fired on its own. `/new-endpoint`; the skill answers to `/java-
  spring:spring-boot-service`. `/review-migration` stays, because it launches
  the subagent.

### Fixed
- `not-fired` eval grader states what a correct answer looks like, not only
  what scores badly.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.

## [0.1.0] — 2026-09-20

### Added
- `spring-boot-service` skill: constructor injection, typed and validated
  configuration properties, layer boundaries, and the four transaction traps —
  self-invocation bypassing the proxy, checked exceptions not rolling back, I/O
  inside a transaction, and `readOnly`.
- `kafka-consumer` skill: built on at-least-once delivery, so idempotency,
  manual acknowledgement, retry versus dead letter, and what renaming a
  consumer group actually does.
- `java-21-modernize` skill: records, sealed types, pattern matching and
  virtual threads — including the five cases where virtual threads are the
  wrong answer, starting with pinning on `synchronized`.
- `test-shape` skill: which level to test at, real infrastructure over H2 and
  mocked brokers, and assertions about behaviour rather than call order.
- `migration-review` subagent: reviews a migration for what breaks during a
  rolling deploy, with the expand/contract split and a required deploy-order
  section.
- `scripts/check_migration.py`: mechanical pass over Flyway SQL and Liquibase
  changesets — non-concurrent index builds, `NOT NULL` without a default,
  drops and renames of columns still in use, unbounded DML, duplicate Flyway
  versions, inline foreign-key validation, missing rollbacks.
- `/review-migration` and `/new-endpoint` commands.
- 18 fixture assertions covering planted unsafe migrations, migrations that are
  genuinely safe and must stay quiet, Liquibase changesets, exit codes and JSON
  output. The suite also audits this plugin's own skills.
