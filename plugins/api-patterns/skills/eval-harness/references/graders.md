# Grader shapes to copy

## Model grader, general quality

```
You are evaluating a response against the criteria below.

<criteria>
{criteria}
</criteria>

<response>
{response}
</response>

First, list what this response does well. Be specific and quote it.
Second, list what it does badly, leaves out, or gets wrong.
Only after both, give a score from 1 to 10 where:
  1-3  fails the criteria
  4-6  meets some of them, with real gaps
  7-8  meets them
  9-10 meets them and handles the hard part well

Return only JSON: {"strengths": "...", "weaknesses": "...", "score": N}
```

The two lists before the number are load-bearing. Without them the scores
collapse toward the middle and stop discriminating.

## Model grader, faithfulness to a source

```
Does every claim in the response appear in the source?

<source>{source}</source>
<response>{response}</response>

List each claim in the response, and for each one: SUPPORTED with the quote
that supports it, or UNSUPPORTED. Then score: 10 if every claim is supported,
0 if any claim is not.
```

Faithfulness is binary in practice. A summary with one invented number is not
a 7.

## Code graders

```python
import ast
import json
import re


def grades_json(output: str) -> float:
    try:
        json.loads(output)
        return 10.0
    except json.JSONDecodeError:
        return 0.0


def grades_python(output: str) -> float:
    try:
        ast.parse(output)
        return 10.0
    except SyntaxError:
        return 0.0


def grades_regex(output: str) -> float:
    try:
        re.compile(output)
        return 10.0
    except re.error:
        return 0.0


def grades_schema(output: str, required: set[str]) -> float:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return 0.0
    return 10.0 if required <= set(data) else 0.0
```

## Combining

```python
score = (code_score + model_score) / 2
```

Say in the report that the code half is 10-or-0. An average of 5 means "parses
but the model grader disliked it" or "does not parse but reads well" — those
are different problems and the mean hides which.
