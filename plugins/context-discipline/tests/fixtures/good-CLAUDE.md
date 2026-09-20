# Project instructions

## Dependencies

Use constructor injection; never `@Autowired` on a field. Fields stay `final`.

## Errors

Never catch an exception without either re-raising it or logging it with the
failing input. An empty catch block fails review.

Return `ProblemDetail` from the `@RestControllerAdvice`; do not build error
bodies in controllers.

## Tests

Every new behaviour gets a test for its failure path, not only its happy path.

Use Testcontainers for the database; do not substitute H2.

## Never

NEVER commit a credential. If one is needed, read it from the environment.
