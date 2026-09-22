---
type: llm
weight: 1
---

The chunk has lost the heading it depended on. Neither of the two options
offered fixes that: larger chunks blur what is retrieved, and a better
embedding model cannot embed information the text does not carry. The fix is
to generate a sentence of context per chunk at ingest and index it with the
chunk.

Score well when the response:
- Names contextual retrieval, or describes it: a generated line of context
  prepended to each chunk before embedding
- Makes clear that the prompt generating it receives the document, or a
  bounded stand-in for it — the opening chunks plus the ones immediately
  before — and not the chunk alone
- Says the contextualised chunk goes into both indexes, or at least into the
  one being searched
- Mentions the ingest cost (one call per chunk), or how to bound it

Score badly when the response:
- Recommends only a different chunk size, an overlap, or another embedding
  model
- Describes generating the context from the chunk by itself, which cannot
  recover a heading the chunk does not contain
- Answers with a general list of RAG improvements without addressing the
  missing heading
