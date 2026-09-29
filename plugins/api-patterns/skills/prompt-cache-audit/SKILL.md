---
name: prompt-cache-audit
description: Checks Claude API calls for prompt caching that silently misses — breakpoints in the wrong place, varying content inside a cached prefix, too many breakpoints, a prefix too short to store. Use when API costs are higher than expected, when adding caching, or when reviewing code that calls the Messages API repeatedly.
allowed-tools: Read, Glob, Grep, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_api_calls.py *)
---

# Auditing prompt caching

Caching fails **silently** when it is configured wrongly. The request
succeeds, the output is fine, and you pay full price plus a write premium on
every call. The only evidence is `cache_read_input_tokens` staying at zero.

Two ways to ask for it:

| | How | Use it for |
|---|---|---|
| **Automatic** | one `cache_control` at the top level of the request | A conversation that grows. The breakpoint lands on the last cacheable block and moves forward by itself |
| **Explicit** | `cache_control` on the blocks you choose, up to four | A prefix you control: tools, a long system prompt, a document |

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_api_calls.py <path>
```

With no path given, audit every file in the repository that calls the Messages
API. The script also reports request shapes that fail when they run — thinking
with `temperature` or a prefill, a thinking budget under 1,024 tokens or with
no room under `max_tokens`, `effort` outside `output_config`, `system=None`,
a tool loop that never returns `is_error`, and the shapes a newer model
rejects — a fixed budget from the 5 family on, disabled thinking or a forced
`tool_choice` on Sonnet 5.5, Opus 5.5 and Fable 5.1.

## The rules

**The prefix order is `tools` → `system` → `messages`.** A breakpoint caches
everything *before* it. Caching a later segment while an earlier one varies
achieves nothing — the prefix no longer matches.

**At most four explicit breakpoints** per request. More is rejected. Put them
on the longest stable prefixes, not on every block.

**A prefix under the model's minimum is not stored at all**, and no error says
so: the breakpoint is simply inert. The floor is per model — 512 tokens on the
lowest, 1,024 on most, 4,096 on some — so look up the one you call instead of
assuming. `cache_creation_input_tokens` at zero on the first call is how you
find out.

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

**A breakpoint on the newest message is normal**, and not a mistake. In a
growing conversation everything before it is unchanged, so the next request
still matches. What breaks it is a *varying* block: a timestamp or a
per-request note in the block the breakpoint sits on has the same effect as
one in the system prompt.

**The entry lives five minutes by default, refreshed on every hit.** A prefix
used once an hour is written and expired repeatedly, never read. A one-hour
lifetime can be asked for — `"cache_control": {"type": "ephemeral", "ttl":
"1h"}` — and the write costs twice the base input price, so it pays off for a
prefix reused across a gap, not for one already hit every few minutes.

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
