---
name: eval-harness
description: Builds a dataset, grader and scoring pipeline for a prompt, so changes are measured instead of eyeballed. Use when a prompt is being tuned, when the user asks whether a change made things better, when output quality is inconsistent, or before shipping anything that depends on a model's output.
allowed-tools: Read, Glob, Grep
---

# Evaluating a prompt

Reading three outputs and deciding it looks better is not evidence. It is the
most common way a prompt gets worse while everyone believes it improved.

The pipeline is four stages: **dataset → model → grader → score.**

## 1. The dataset

Twenty to thirty cases is enough to see a real change. Start smaller — five to
ten — while the prompt is still moving.

What goes in it:

- The ordinary cases, in the proportion they actually occur
- **The edge cases you already know about**: empty input, the maximum length,
  the ambiguous request, the hostile one
- Cases the current prompt gets wrong. Those are the ones that show movement.

Keep it in a file, not in the conversation. An eval you cannot re-run is a
one-off opinion.

## 2. Graders

Use both kinds and average them. They fail in different directions, which is
the point.

### Code graders — for anything verifiable

Deterministic, free, and worth far more than they cost:

```python
def grade_json(output: str) -> float:
    try:
        json.loads(output)
        return 10.0
    except json.JSONDecodeError:
        return 0.0
```

`json.loads`, `ast.parse`, `re.compile`, a schema check, an exact-match
lookup. **Ten or zero** — there is no partial credit on whether something
parses, and pretending otherwise hides failures in an average.

### Model graders — for everything else

For tone, completeness, faithfulness, helpfulness. One rule matters more than
the rest:

**Ask for the reasoning before the number.** A grader asked only to score
returns something near 6 for almost everything, and a flat score measures
nothing. Make it name strengths, then weaknesses, then the score:

```
Evaluate the response against the criteria below.

First: what does this response do well? Be specific.
Then: what does it do badly, or leave out?
Finally, and only then: a score from 1 to 10.

Return JSON: {"strengths": "...", "weaknesses": "...", "score": N}
```

The order is the mechanism. Reversing it gets you a number with a
justification attached, which is a different and much weaker thing.

### Human graders

For the handful of cases where judgement is the whole point. Expensive, so
spend it on a sample, not the suite.

## 3. Scoring

Average the code grader and the model grader. Report the distribution, not
only the mean — a prompt that scores 7 on everything is a different problem
from one that scores 10 on most and 2 on a few.

## 4. Comparing

Always against a baseline. "Version B scores 7.9" means nothing; "7.9 against
A's 3.9 on the same thirty cases" is a result.

Change one thing at a time. Two changes and one number tells you nothing about
either.

## Where prompts actually improve

Measured against the same dataset, the same prompt at three levels of effort:

| | Score |
|---|---|
| Vague instruction | 2.3 |
| Clear and specific, with an output guide | 3.9 |
| Plus structure, examples and step ordering | 7.9 |

The jump is in the third row, and it comes from examples of the output you
want — not from more adjectives about quality.

## Running it

`scripts/` in this plugin has no runner on purpose: the pipeline belongs in
your repo, in your language, with your cases. `references/graders.md` has
grader prompts and code-grader shapes to copy.

## What not to do

- Score by reading a few outputs
- Change the dataset and the prompt together, then compare the numbers
- Use a model grader with no reasoning step
- Average a 10-or-0 code grader into a 1–10 model grader without saying so
