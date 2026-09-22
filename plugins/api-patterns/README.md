# api-patterns

Patterns for building on the Claude API that carry their own verification.

```
/plugin install api-patterns@pacoromerodev
```

## Components

| Component | Type | Fires when |
|---|---|---|
| `eval-harness` | Skill | Tuning a prompt; asking whether a change helped |
| `prompt-cache-audit` | Skill | Costs higher than expected; adding caching |
| `rag-retriever` | Skill | Building or debugging retrieval |
| `agent-or-workflow` | Skill | Designing anything that calls a model more than once |
| `tool-schema-review` | Subagent | Tools added or changed; a tool never called |

## Graders that discriminate

The rule that decides whether a model grader is worth running: **ask for the
reasoning before the number.** A grader asked only to score returns something
near 6 for almost everything, and a flat score measures nothing. Strengths,
then weaknesses, then the score — in that order, because the order is the
mechanism.

Code graders are **10 or 0**. Whether something parses has no partial credit,
and pretending otherwise hides failures inside an average.

## Caching fails silently

```bash
python3 plugins/api-patterns/scripts/check_api_calls.py src/
```

A misconfigured breakpoint does not error. The request succeeds, the output is
fine, and you pay full price plus a write premium every call.

| Finding | Effect |
|---|---|
| A timestamp, uuid or random value inside a cached prefix | **Worse than no caching** — written every call, read never |
| More than four breakpoints | Request rejected |
| Prefix under the model's minimum (512–4,096 tokens) | Breakpoint accepted and inert, with no error |
| Breakpoint on a block that varies per request | The hash differs every time: written, never read |
| Thinking with `temperature`, or with a prefilled turn | Rejected, or silently unsupported |
| A thinking budget under 1,024, or not below `max_tokens` | Rejected, or no room left for the answer |
| `effort` outside `output_config` | An unexpected keyword |
| `system=None` | An error, not an omission |
| A tool loop with no `is_error` | A failed tool leaves the model waiting or inventing |
| `cache_control` with usage never read | A cache that never hits looks exactly like one that works |

`cache_read_input_tokens` above zero is the only proof.

## Hybrid retrieval, fused by rank

```bash
python3 plugins/api-patterns/scripts/fuse.py rankings.json
```

Embeddings miss the queries that should be easiest — identifiers like
`ERR_4032`, rare proper nouns, exact quoted phrases. BM25 catches all three, so
it is not a fallback but the other half.

Do not try to combine a cosine score with a BM25 score; they are not on the
same scale. Combine the **ranks**:

```
score(d) = Σ 1 / (k + rank(d, r))       k ≈ 60
```

Two properties make it the default: no calibration is needed, and **agreement
wins** — a document both retrievers rank well beats one that only one of them
put first.

## Workflow or agent

If you know the steps, write a workflow: more precise, cheaper, testable, and
it fails reproducibly. The honest test is to write the steps down — if you can,
that is your workflow. If the fourth depends on what the first three found, you
have an agent, and you now know which part needs the freedom.

## Tests

```bash
plugins/api-patterns/tests/run.sh
```

27 assertions. The caching fixtures come in both directions, and the RRF tests
check the property the whole choice rests on: `s2` at semantic#1 and bm25#2
must outrank `s7` at bm25#1. Plus duplicates, single lists, tie determinism,
`k=0` and `limit`.

## Evals

```bash
claude plugin eval plugins/api-patterns --scaffold --allow-tools Bash
```

- **cache-silently-missing** — a timestamp in a cached prefix; the answer must
  say it is worse than not caching, and how to verify the fix.
- **workflow-not-agent** — a task with fully known steps, asked as "how should
  I structure the agent loop". The answer must push back.
- **agent-that-must-resume** — a multi-hour clean-up agent that died mid-run.
  The answer must reach managed agents, and must not offer the tool runner as
  the fix for resumption.
- **bedrock-model-not-found** — "the model doesn't exist", with IAM already
  correct. The answer must reach the cross-region inference profile.
- **not-fired** — "how many tokens is a page of text", which must not start an
  audit.

## Requirements

Python 3.8+ on `PATH`. Standard library only.
