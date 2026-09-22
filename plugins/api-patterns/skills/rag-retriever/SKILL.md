---
name: rag-retriever
description: Designs retrieval for a RAG system — chunking, embeddings, keyword search and fusing the two — and says which failure each part fixes. Use when building or debugging retrieval, when search misses documents that obviously match, or when deciding how to chunk a corpus.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fuse.py *)
---

# Retrieval that finds the right thing

Most RAG problems are retrieval problems. The model can only work with what it
was handed.

## Chunking

| Strategy | Good for | Cost |
|---|---|---|
| Fixed size with overlap | Anything, as a baseline | Cuts mid-sentence, mid-table |
| By structure (heading, section) | Documentation, manuals, legal text | Uneven sizes |
| By sentence or paragraph | Prose | Loses wider context |
| Semantic (split where meaning shifts) | Mixed corpora | Slow and expensive to build |

Start with structure if the documents have any, fixed size with overlap if they
do not. Overlap of 10–20% stops an answer being cut in half by a boundary.

**Store the text alongside its embedding.** A vector you cannot turn back into
readable text is useless at answer time, and re-fetching by id is a join you
will regret.

## Embeddings and similarity

Embed with a model built for retrieval. **Cosine similarity** is the measure:
values from −1 to 1, higher is closer. Distance is `1 − similarity` when you
need a distance.

Embed the chunk *and the query* with the same model. Mixing models produces
numbers that look fine and mean nothing.

## What embeddings miss

Semantic search fails on exactly the queries that should be easiest:

- Identifiers: `ERR_4032`, `CVE-2024-1234`, an order number
- Rare proper nouns the embedding model never saw
- Exact phrases the user is quoting

**BM25** handles all three, because it matches terms rather than meaning. It is
not a fallback — it is the half that catches what embeddings structurally
cannot.

## Fusing the two: RRF

Do not try to combine a cosine score with a BM25 score. They are not on the
same scale and normalising them is guesswork. Combine the **ranks**:

```
score(d) = Σ  1 / (k + rank(d, r))
          r
```

over each retriever `r` where document `d` appears, rank starting at 1, `k`
around 60.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fuse.py rankings.json
```

Two properties are why this is the default:

- **No calibration needed.** Ranks are comparable; scores are not.
- **Agreement wins.** A document both retrievers rank well beats one that only
  one of them ranked first. That is usually the right answer, and it is what
  `k` is tuning — at 60 the gap between rank 1 and rank 2 is small enough for
  agreement to outweigh position.

## Re-ranking

After fusion, a model can re-rank the top 20 down to the 5 you actually send.
Ask it for ids in order, not scores — ordering is what it is good at.

Worth it when precision matters more than latency, since it costs a model call.

## Contextual retrieval

A chunk taken out of its document loses what it was about. "It must be renewed
90 days before expiry" — what must? Prepend one generated sentence of context
to each chunk before you embed it, and index the pair.

The prompt needs both halves, or the model has nothing to place the chunk
against:

```
<document>{document}</document>

<excerpt>{chunk}</excerpt>

The excerpt comes from the document above. Name, in one or two sentences, what
part of it this is and what it refers to, so that someone reading the excerpt
alone would know. Reply with those sentences only.
```

Prepend the reply to the chunk, embed that, and keep the same pair in the
keyword index.

**When the document will not fit:** pass its first few chunks, which usually
carry the title and summary, together with the handful immediately before this
one. That is enough to place it, and it is bounded.

**Cost:** one model call per chunk, at ingest. Cache the document part of the
prompt and the calls for one document share it.

## Debugging retrieval

When an answer is wrong, check retrieval before blaming the prompt:

1. Is the right chunk in the index at all?
2. Does it come back for the exact query, at any rank?
3. Does it come back for a paraphrase?

Failing 1 is a chunking or ingest bug. Failing 2 and not 3 means keyword search
is missing. Failing 3 and not 2 means the embeddings are.
