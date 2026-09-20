---
type: llm
weight: 1
---

The description is `Kafka consumer helper.` — four words, no trigger, nothing
for a prompt to match against.

Score well when the response:
- Produces a description that says both what the skill does and when to use it
- Phrases the trigger in words a user would actually type — writing a consumer,
  a listener not acking, messages being reprocessed, setting up a DLT — rather
  than restating "Kafka consumer"
- Offers more than one candidate and says what each would and would not match,
  including likely false positives
- Recommends one, with a reason

Score badly when the response:
- Returns a single rewrite with no reasoning about coverage
- Produces a longer definition that still never names a situation
- Rewrites the body instead of the description
