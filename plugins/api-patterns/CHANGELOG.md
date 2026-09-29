# Changelog

All notable changes to `api-patterns`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-09-29

### Added
- Three cases: `cache-ttl-mismatch`, `hybrid-or-rerank` and `tool-never-chosen`,
  the last for the subagent, which had none. Every skill in this plugin now has the
  two positive cases and one negative that CONTRIBUTING has always
  asked for.

### Changed
- Marked **experimental** in the README, the manifest and the marketplace
  entry. Across its ten cases it scores below the no-plugin baseline (Δ −0.10,
  Sonnet judging); the README says so, and says what would settle it.
- `tool-schema-review` no longer has `Bash`. It reviews what the model sees —
  name, description, schema — and never runs anything, so the tool was a
  grant with no use.
- Reworded four runs of five words that also appear in the English lessons,
  found once the wording check read them (`eval-harness`, its providers
  reference, and this changelog).

- `tool-schema-review` says where the tools it reviews live — the `tools`
  array of a Messages call, or the functions a tool runner builds one from —
  and points at `mcp-review` for the other kind.
- `bedrock-model-not-found`'s criteria no longer contradict each other: they
  failed any answer that mentioned IAM or model access while asking only that
  neither come first. An answer that leads with the inference profile and
  notes the IAM condition later now passes.
- `tool-schema-review` no longer points at `mcp-review`: mcp-builder was
  retired on 2026-09-25 and the subagent went with it.
- `eval-harness` credits the score jump to the right technique. The move from
  about 3.9 to about 7.9 comes from explicit output guidelines — a length, a
  structure, the elements the answer must contain, or the steps to work
  through — not from examples, which the skill previously named. Examples are
  now what you add next, for the edge cases and formats the guidelines cannot
  carry, and the skill says to take them from the highest-scoring outputs
  already in the eval rather than inventing them. It also says how to have a
  fast model draft the dataset, and what to check before trusting it.
- `prompt-cache-audit` and `check_caching.py` match the API as documented
  today. Caching is not "never automatic": one `cache_control` at the top
  level of a request caches the growing history by itself, and the skill now
  says when to use that instead of explicit breakpoints. The minimum cacheable
  prefix is per model — 512 to 4,096 tokens — not a single figure. The
  five-minute lifetime is named as the default, with the one-hour option and
  what it costs.
- The `cache-on-tail` warning is gone, and `volatile-breakpoint` replaces it.
  A breakpoint on the newest message is the normal pattern for a conversation:
  everything before it is unchanged, so the next request still hits. The fault
  is a block that varies — a timestamp in the message the breakpoint sits on
  behaves exactly like one in the system prompt. Two new fixtures,
  `growing_conversation.py` and `varying_tail.py`, hold the distinction.
- `rag-retriever`: the contextual-retrieval prompt now carries the document,
  not only the chunk. Generating context from the chunk alone cannot recover a
  heading the chunk does not contain, which is the case the technique exists
  for. The skill says what to pass when the document will not fit, what to
  index, and what the ingest costs — and it is written in this repository's
  own words, which the new wording check now enforces.

### Fixed
- `not-fired` eval grader states what a correct answer looks like, not only
  what scores badly.

### Security
- Skills no longer pre-approve a bare `Bash`, `Write` or `Edit`. `allowed-tools`
  grants tools without a prompt on the turn a skill fires; it restricts
  nothing. Read tools stay pre-approved, and Bash only for the plugin's own
  script, as an exact prefix. Everything else goes through the normal prompt.

## [0.1.0] — 2026-09-20

### Added
- `eval-harness` skill: dataset → model → grader → score. It carries the rule
  deciding whether a model grader discriminates at all — reasoning before the
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
