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

**Generating it.** Writing thirty cases by hand is where most evals die, so
have a fast, cheap model write the first draft: ask for a JSON array, one
object per case, with the fields your runner reads and one worked example of
the shape. Say what a solvable case looks like for your task, or you get
thirty variations of the same easy one. Ask for the array through structured
outputs (`output_config.format` with the case schema) so it always parses;
current models reject a prefilled assistant turn. Then read the cases
yourself: you are looking for the ones that are too easy, and for the edge
case the model did not think to write.

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

Vary a single variable per run. Two changes and one number tells you nothing
about either.

## Where prompts actually improve

The same prompt, the same dataset, three levels of effort:

| | Score |
|---|---|
| Vague request | 2.3 |
| An instruction, not a question: an action verb, the task in the first line | 3.9 |
| Plus explicit output guidelines | 7.9 |

The big jump is the third row, and it is not "more adjectives about quality".
It is naming what the output must satisfy — length, structure, the elements it
has to contain, the tone — or the steps to work through when the task needs
thinking, rather than describing the result you hope for. "Under 1,000 words,
one scene that shows the talent, at least one secondary character" moves a
score; "well written" does not.

**Examples come next, not instead.** Once the guidelines are in place, add one
or more worked examples for the cases they cannot carry: an edge case, an
exact output format, a tone, an ambiguous input. Wrap each in tags that mark
the input and the ideal answer, say plainly that it is an example with the
answer you want, and say *why* that answer is the right one.

The eval is where the examples come from. The cases the current prompt already
scores highest are, by definition, outputs you would be happy to receive —
lift those into the prompt rather than inventing new ones, and keep them
covering the failures you actually see.

## Running it

`scripts/` in this plugin has no runner on purpose: the pipeline belongs in
your repo, in your language, with your cases. `references/graders.md` has
grader prompts and code-grader shapes to copy.

**On Bedrock or Vertex**, the request shape differs enough to make a ported
eval incomparable, and one failure — a model not hosted in your region —
reports itself as a model that does not exist. `references/providers.md` has
both, and what to record alongside a score.

## What not to do

- Score by reading a few outputs
- Change the dataset and the prompt together, then compare the numbers
- Use a model grader with no reasoning step
- Average a 10-or-0 code grader into a 1–10 model grader without saying so
