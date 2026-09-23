---
type: llm
weight: 1
---

Reranking reorders what was retrieved. If the ticket carrying that exact
code never came back, no amount of reordering finds it. Identifiers are the
canonical case for keyword search, which matches terms rather than meaning,
fused with the vector results by rank.

Score well when the response:
- Says reranking cannot recover a document that was not retrieved
- Names keyword search (BM25 or equivalent) as what matches an exact
  identifier, and says why embeddings structurally miss them
- Describes fusing the two by rank rather than by score, because the two
  scores are not on a comparable scale
- May still recommend reranking, but afterwards and for a different reason

Score badly when the response:
- Agrees that reranking will fix it
- Recommends a different embedding model as the fix
- Describes normalising the two scores and combining them
