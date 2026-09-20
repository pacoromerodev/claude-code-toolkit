---
name: java-21-modernize
description: Applies modern Java language features — records, sealed types, pattern matching, text blocks, virtual threads — and says when each one is the wrong choice. Use when modernising older Java code, when the user asks whether to use a record, a sealed interface or virtual threads, or when reviewing code that could be simpler on Java 17 or 21.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Modern Java, and when not to

Check the target first — `maven.compiler.release`, or the Gradle toolchain.
Suggesting a Java 21 feature to a project pinned at 17 wastes everyone's time.

## Records

For anything whose identity is its values: DTOs, responses, value objects,
configuration properties, keys in a map.

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        if (amount.scale() > currency.getDefaultFractionDigits()) {
            throw new IllegalArgumentException("too many decimal places");
        }
    }
}
```

The compact constructor is the right place for validation — it runs before the
fields are assigned, so an invalid record cannot exist.

**Not a record when:** the type is a JPA entity — it needs a no-arg constructor
and mutable fields, and Hibernate cannot proxy a final class. Not when identity
is an id rather than the values.

## Sealed types with pattern matching

When a type has a known, closed set of cases:

```java
public sealed interface PaymentResult
        permits Authorised, Declined, RequiresAction {}

String describe(PaymentResult result) {
    return switch (result) {
        case Authorised a -> "authorised " + a.reference();
        case Declined d -> "declined: " + d.reason();
        case RequiresAction r -> "action needed at " + r.redirectUrl();
    };
}
```

The value is exhaustiveness: add a case to the interface and every switch stops
compiling until it is handled. That is a whole class of bug the compiler now
finds instead of production.

**Not sealed when** the set is genuinely open to extension — you are then
fighting the design, not expressing it.

## Pattern matching and `var`

`instanceof` with a binding removes the cast. `var` where the type is obvious
from the right-hand side, spelled out where it is not: `var result = service.process(x)`
tells the reader nothing.

## Text blocks

For SQL, JSON and anything multi-line. Watch the incidental indentation — the
closing delimiter's position sets the margin.

## Virtual threads — read this before reaching for them

Java 21. For I/O-bound work: a thread parked on a socket costs almost nothing,
so thousands of concurrent requests stop needing a pool.

```java
spring.threads.virtual.enabled=true
```

**They are the wrong answer more often than the enthusiasm suggests:**

1. **Pinning on `synchronized`.** A virtual thread that blocks inside a
   `synchronized` block pins its carrier thread, and the benefit evaporates. If
   the hot path has `synchronized`, move to `ReentrantLock` first — otherwise
   you can end up slower than before.
2. **A pooled JDBC connection is still the limit.** Ten thousand virtual
   threads against a pool of twenty wait on the pool. The bottleneck moved, it
   did not disappear.
3. **CPU-bound work gains nothing.** You have as many cores as you have.
4. **ThreadLocal caching becomes a leak.** Objects cached per thread, with
   millions of threads, no longer amortise anything.
5. **Do not pool them.** Creating one is cheap; that is the point. Pooling
   virtual threads reintroduces the cost you removed.

Measure before and after. Virtual threads are a change to make with a number in
front of you, not on principle.

## Other things worth knowing

- **`Optional`** as a return type, never as a field or a parameter
- **Streams** where they are clearer than a loop, and not where they are not —
  a stream with a side effect in `forEach` is a loop wearing a costume
- **`Objects.requireNonNull`** at constructor boundaries
- **`List.of` / `Map.of`** for immutable literals, remembering they reject nulls

## What to check before calling it done

- The language level actually supports what you used
- No record where a JPA entity is needed
- No virtual threads without a measurement, and no `synchronized` on the path
- Behaviour unchanged: modernising is a refactor, and the tests should not need
  editing to keep passing
