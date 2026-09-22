---
name: spring-boot-service
description: Conventions for writing or reviewing a Spring Boot service class, REST controller or configuration. Use when adding an endpoint, a service or a repository, when wiring configuration, when deciding where a transaction boundary goes, or when the user asks how something should be structured in a Spring Boot application.
allowed-tools: Read, Glob, Grep
---

# Spring Boot services

Rules that hold at any company. Where a project's own conventions differ, the
project wins — read its existing code first.

## Dependency injection

**Constructor injection, always.** Never `@Autowired` on a field.

```java
@Service
public class PricingService {
    private final PriceRepository repository;
    private final DiscountPolicy policy;

    public PricingService(PriceRepository repository, DiscountPolicy policy) {
        this.repository = repository;
        this.policy = policy;
    }
}
```

Fields stay `final`, the object cannot exist half-built, and the class is
constructible in a test without a Spring context. Field injection gives up all
three, and hides that a class has grown eleven dependencies — a constructor
makes that impossible to miss.

Single constructor needs no `@Autowired`. Do not add Lombok's
`@RequiredArgsConstructor` to a class that does not already use Lombok.

## Configuration

`@ConfigurationProperties` over scattered `@Value`:

```java
@ConfigurationProperties(prefix = "pricing")
@Validated
public record PricingProperties(
        @NotNull Duration cacheTtl,
        @Min(0) int maxDiscountPercent) {
}
```

Bound once, validated at startup, typed, and visible as one object. A
misconfigured `@Value` fails at first use, which may be in production at 3am;
`@Validated` properties fail the context on boot.

Never `@Value` a secret. It comes from the environment or a secret manager.

## Layers

| Layer | Holds | Never holds |
|---|---|---|
| Controller | HTTP mapping, validation, status codes | Business rules |
| Service | Business rules, transaction boundaries | HTTP or persistence types |
| Repository | Queries | Rules |

An entity must not leave the service layer. Map to a response record — an
entity as a response body leaks the schema into your API contract, and every
column rename becomes a breaking change.

## Transactions

`@Transactional` goes on the **service** method, not the controller and not the
repository. One business operation, one transaction.

Four things that catch people out:

1. **Self-invocation does nothing.** Calling `this.other()` bypasses the proxy,
   so its `@Transactional` never applies. Move it to another bean.
2. **Only `RuntimeException` rolls back** by default. A checked exception
   commits unless you write `@Transactional(rollbackFor = ...)`.
3. **No I/O inside a transaction.** An HTTP call inside one holds a database
   connection for the length of someone else's timeout.
4. **`readOnly = true`** on reads: it lets the driver and Hibernate skip dirty
   checking, and it documents intent.

## Errors

One `@RestControllerAdvice` mapping exceptions to responses. Do not build
`ResponseEntity` error bodies in each controller.

Never catch, log and continue with a half-built result. Either handle the
failure or let it propagate — a swallowed exception becomes a bug report six
weeks later with nothing in the logs.

Return RFC 7807 `ProblemDetail`. It is built into Spring 6.

## Validation

`@Valid` on the request body, constraints on the record. Validate at the edge
so the service can assume its input is well-formed.

## What to check before calling it done

- No field injection anywhere in the diff
- No entity in a controller signature
- `@Transactional` on services only, and no I/O inside one
- No secret in `application.yml`
- New endpoint: validated input, mapped errors, and a test for the failure path
  as well as the happy one
