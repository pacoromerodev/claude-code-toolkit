---
type: llm
weight: 1
---

Records are not a Lombok replacement in general: they are final, their
fields are final, and they carry value semantics. That makes them right for
the classes that are genuinely values — DTOs, keys, immutable results — and
wrong for anything mutable or extended, such as a JPA entity, which needs a
no-args constructor and non-final fields.

Score well when the response:
- Distinguishes the two cases rather than picking a side
- Names the classes records fit: immutable carriers, DTOs, map keys, results
- Names where they do not: JPA entities, anything mutated after construction,
  anything relying on inheritance
- Mentions what comes with a record — the canonical constructor as the place
  for validation, and value-based equality
- Suggests starting with the DTOs, which are the lowest-risk conversion

Score badly when the response:
- Says to convert everything, or nothing
- Recommends records for JPA entities
- Compares the two only by lines of code saved
