---
type: llm
weight: 1
---

Two changes, one number. The examples may have done nothing; the output
guidelines — a length, a required first line, a required element — are the
change that usually moves a score of this size, and the question assumes the
opposite. Adding ten more examples is a guess dressed as a plan.

Score well when the response:
- Says the two changes cannot be told apart from one score, and that the
  attribution is unsupported
- Proposes measuring them separately: revert one, re-run the same dataset,
  compare
- Says that explicit output guidelines are what typically account for a jump
  of this size, and examples are what you add afterwards for edge cases,
  formats, tone or ambiguity
- If it recommends more examples at all, says where they should come from —
  the highest-scoring outputs already in the eval — rather than inventing them

Score badly when the response:
- Agrees that examples are what worked, or recommends more of them without
  separating the two changes first
- Suggests changing the dataset and the prompt together
- Answers with generic prompt-engineering advice that never addresses the
  attribution problem
