# Changelog

All notable changes to `api-patterns`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-09-20

### Added
- `eval-harness` skill: dataset → model → grader → score, with the rule that
  decides whether a model grader discriminates at all — reasoning before the
  number, strengths then weaknesses then score. Code graders are 10-or-0.
  Grader prompts in `references/graders.md`, loaded on demand.
- `prompt-cache-audit` skill + `scripts/check_caching.py`: finds breakpoints
  that cannot hit, varying content inside a cached prefix, more than four
  breakpoints, prefixes too short to store, and caching that is never
  verified against `cache_read_input_tokens`.
- `rag-retriever` skill: chunking by what the corpus is, why BM25 catches what
  embeddings structurally cannot, and RRF as the way to combine them without
  calibrating incomparable scores.
- `scripts/fuse.py`: Reciprocal Rank Fusion, importable and with a CLI, that
  reports which retriever found each document and where.
- `agent-or-workflow` skill: if you know the steps, write a workflow — with
  the four workflow patterns and what an agent actually needs.
- `tool-schema-review` subagent: judges each tool by what the model sees, and
  returns rewritten descriptions rather than advice to write them.
- `/eval` and `/cache-audit` commands.
- 15 fixture assertions covering both scripts, including RRF edge cases.

### Fixed before release
- The caching auditor measured the **source length** of a system prompt, so a
  prefix built from a module-level constant was reported as too short to
  cache. It now computes a length only when every part is a literal, and stays
  quiet otherwise.
