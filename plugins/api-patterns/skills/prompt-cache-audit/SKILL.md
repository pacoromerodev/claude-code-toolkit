---
name: prompt-cache-audit
description: Checks Claude API calls for prompt caching that silently misses — breakpoints in the wrong place, varying content inside a cached prefix, too many breakpoints, a prefix too short to store. Use when API costs are higher than expected, when adding caching, or when reviewing code that calls the Messages API repeatedly.
allowed-tools: Read, Glob, Grep, Bash
---

# Auditing prompt caching

Caching is **never automatic**, and when it is configured wrongly it fails
**silently**. The request succeeds, the output is fine, and you pay full price
plus a write premium on every call. The only evidence is
`cache_read_input_tokens` staying at zero.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_caching.py" <path>
```

## The rules

**The prefix order is `tools` → `system` → `messages`.** A breakpoint caches
everything *before* it. Caching a later segment while an earlier one varies
achieves nothing — the prefix no longer matches.

**At most four breakpoints** per request. More is rejected. Put them on the
longest stable prefixes, not on every block.

**A prefix under about 1024 tokens is not stored at all.** The breakpoint is
accepted and inert. (Smaller models have a higher floor — check the current
figure for the model you are using rather than assuming.)

**Everything before a breakpoint must be byte identical across calls.** This
is where caching actually dies:

```python
system=[{
    "type": "text",
    "text": f"You are a support agent. Today is {datetime.now()}.",
    "cache_control": {"type": "ephemeral"},
}]
```

That timestamp changes every call, so the prefix never matches, and you pay
the **write** premium every single time — strictly worse than not caching. A
user id, a session id, a random seed, a formatted date: same result.

Move the varying part after the breakpoint, into the messages.

**The cache entry expires on a timer, refreshed on each hit.** A prefix used
once an hour is written and expired repeatedly, never read. Caching pays off
under sustained traffic, not occasional calls.

## Verify it worked

```python
response = client.messages.create(...)
print(response.usage.cache_creation_input_tokens)  # written
print(response.usage.cache_read_input_tokens)      # read — the one that matters
```

`cache_read_input_tokens` above zero is the only proof. Log it once when
adding caching: a cache that silently never hits looks exactly like one that
works.

## What to cache

Good: a long system prompt, a tool array, a document being asked about
repeatedly, few-shot examples.

Not worth it: anything short, anything that varies, anything called rarely.

## Reporting

Lead with breakpoints that cannot hit — those cost money now. Then the ones
that are inert. Say what `cache_read_input_tokens` should be checked against
after the fix.
