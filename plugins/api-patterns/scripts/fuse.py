#!/usr/bin/env python3
"""Reciprocal Rank Fusion: combine several rankings into one.

    python3 fuse.py rankings.json
    python3 fuse.py rankings.json --k 60 --limit 10

Input is a JSON object mapping a retriever name to its ranked list of ids,
best first:

    {"semantic": ["s2", "s6", "s7"], "bm25": ["s7", "s2", "s9"]}

RRF scores each id as the sum over retrievers of 1 / (k + rank), rank starting
at 1. Two properties make it the right default for hybrid retrieval:

  - It needs no score calibration. A cosine similarity and a BM25 score are
    not comparable numbers; their *ranks* are.
  - A document ranked well by two retrievers beats one ranked first by only
    one. Agreement counts for more than any single position.

`k` damps the top of each list. At k=60, the gap between rank 1 and rank 2 is
small enough that a document both retrievers like outranks one that only one
of them put first — which is the behaviour you want.

Importable as `fuse(rankings, k, limit)`.
"""
import argparse
import json
import sys
from pathlib import Path

DEFAULT_K = 60


def fuse(rankings, k=DEFAULT_K, limit=None):
    """Fuse ranked id lists into one ranking.

    rankings: {retriever_name: [id, ...]} with the best result first.
    Returns [(id, score, {retriever: rank}), ...] sorted by score descending.
    Ties break on the id, so the output is deterministic.
    """
    if k <= 0:
        raise ValueError("k must be positive")

    scores, positions = {}, {}
    for name, ids in rankings.items():
        seen = set()
        for index, doc_id in enumerate(ids, start=1):
            if doc_id in seen:      # a repeat in one list must not score twice
                continue
            seen.add(doc_id)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + index)
            positions.setdefault(doc_id, {})[name] = index

    ordered = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    if limit is not None:
        ordered = ordered[:limit]
    return [(doc_id, score, positions[doc_id]) for doc_id, score in ordered]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="JSON file: {retriever: [id, ...]}")
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        rankings = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except Exception as error:
        print(f"cannot read {args.path}: {error}", file=sys.stderr)
        return 1

    if not isinstance(rankings, dict) or not rankings:
        print("expected a non-empty object mapping retriever names to id lists",
              file=sys.stderr)
        return 1

    for name, ids in rankings.items():
        if not isinstance(ids, list):
            print(f"{name!r} is not a list of ids", file=sys.stderr)
            return 1

    try:
        results = fuse(rankings, k=args.k, limit=args.limit)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([
            {"id": doc_id, "score": round(score, 6), "ranks": ranks}
            for doc_id, score, ranks in results
        ], indent=2))
        return 0

    width = max((len(str(doc_id)) for doc_id, _, _ in results), default=2)
    print(f"{'id'.ljust(width)}  score     ranks")
    for doc_id, score, ranks in results:
        detail = ", ".join(f"{name}#{rank}" for name, rank in sorted(ranks.items()))
        print(f"{str(doc_id).ljust(width)}  {score:.6f}  {detail}")

    covered = [doc_id for doc_id, _, ranks in results if len(ranks) > 1]
    if covered:
        print()
        print(f"Found by more than one retriever: {', '.join(map(str, covered))} "
              f"— agreement is what RRF rewards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
