#!/usr/bin/env python3
"""Audit Claude API calls for the mistakes that cost money or fail late.

    python3 check_api_calls.py client.py
    python3 check_api_calls.py src/ --json

Two kinds of fault. A request shaped wrongly — thinking with temperature, a
budget under the floor, `effort` outside `output_config`, `system=None` —
fails when it runs, which is usually in front of someone. Caching fails
quietly: a request with a breakpoint in the wrong place simply
misses, every time, and the only evidence is `cache_read_input_tokens` staying
at zero on a bill that does not go down.

The rules checked here:

  - Breakpoints are placed on a prefix, and the prefix order is
    tools → system → messages. Anything before a breakpoint must be byte
    identical across calls.
  - At most 4 explicit breakpoints per request.
  - A cached prefix under the model's minimum is never stored at all, and no
    error is returned.
  - Anything that changes per call — a timestamp, a user id, a random value —
    inside a cached prefix invalidates it on every request. That is true
    wherever the breakpoint sits, including on the newest message.
  - Extended thinking rules out `temperature` and a prefilled assistant turn;
    its budget starts at 1,024 tokens and must leave room under max_tokens;
    `effort` lives in `output_config`.
  - `system=None` is an error rather than an omission.
  - Newer models reject shapes older ones took: a fixed `budget_tokens`
    from the 5 family on, and on Claude Sonnet 5.5, Opus 5.5 and Fable 5.1
    disabled thinking and a forced `tool_choice`. Sonnet 5.5 turns
    thinking off with `between_tools`, at effort high or below.
  - A tool loop returns a result for a tool that failed, with is_error.

Parses with `ast`. Exit 1 on an error, 0 otherwise.
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

MAX_BREAKPOINTS = 4

# The minimum cacheable prefix is per model: 512 tokens on the smallest floor,
# 4,096 on the largest, 1,024 on most. Below it the breakpoint is accepted,
# nothing is stored, and no error comes back. The hint uses the common figure
# and says to check the model.
MIN_TOKENS_HINT = 1024

# Values that differ between two otherwise identical requests. Any of these
# inside a cached prefix means the prefix never matches twice.
VOLATILE = re.compile(
    r"\b(datetime\.now|time\.time|utcnow|uuid[0-9]?|uuid4|random\.|token_hex"
    r"|timestamp|now\(\))", re.I)


class Finding:
    def __init__(self, level, file, line, rule, message, hint):
        self.level, self.file, self.line, self.rule = level, file, line, rule
        self.message, self.hint = message, hint

    def as_dict(self):
        return {"level": self.level, "file": self.file, "line": self.line,
                "rule": self.rule, "message": self.message, "hint": self.hint}


def is_messages_create(node):
    """A `client.messages.create(...)` or `.stream(...)` call."""
    target = node.func
    if not isinstance(target, ast.Attribute) or target.attr not in {"create", "stream"}:
        return False
    owner = target.value
    return isinstance(owner, ast.Attribute) and owner.attr in {"messages", "beta"}


def keyword(node, name):
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


def has_cache_control(node):
    return "cache_control" in ast.dump(node)


def count_breakpoints(node):
    return ast.dump(node).count("'cache_control'")


def literal_length(node):
    """Characters we can be sure of, or None when the runtime value is unknown.

    `system=[{"text": AGENT_BRIEF}]` and `"x" * 3000` both have short source
    text and unknown length. Measuring the source instead of the value is how
    a heuristic tells you a 6000-character prompt is too short to cache.
    """
    total = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.Name, ast.Call, ast.BinOp, ast.JoinedStr,
                              ast.Attribute, ast.Starred)):
            return None
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            total += len(child.value)
    return total


def source_of(segment, source):
    try:
        return ast.get_source_segment(source, segment) or ""
    except Exception:
        return ""


def check_call(node, file, source, findings):
    tools = keyword(node, "tools")
    system = keyword(node, "system")
    messages = keyword(node, "messages")

    cached_parts = []
    for name, value in (("tools", tools), ("system", system), ("messages", messages)):
        if value is not None and has_cache_control(value):
            cached_parts.append(name)

    total = count_breakpoints(node)
    if total == 0:
        # Not using caching is a choice, not a mistake — but a large static
        # system prompt sent repeatedly is worth flagging once.
        if system is not None:
            known = literal_length(system)
            if known is not None and known > 2000:
                findings.append(Finding(
                    "info", file, node.lineno, "uncached-prefix",
                    f"system prompt of roughly {known} characters with no "
                    f"cache_control",
                    "If this prefix is identical across calls, a breakpoint on "
                    "it is the cheapest change available. For a growing "
                    "conversation, one cache_control at the top level of the "
                    "request caches automatically and moves the breakpoint "
                    "forward as the history grows."))
        return

    if total > MAX_BREAKPOINTS:
        findings.append(Finding(
            "error", file, node.lineno, "too-many-breakpoints",
            f"{total} cache_control breakpoints; the maximum is "
            f"{MAX_BREAKPOINTS}",
            "The request is rejected. Cache the longest stable prefixes, not "
            "every block."))

    # --- ordering ---
    # The prefix is tools → system → messages. Caching a later part while an
    # earlier one stays uncached still works, but caching `tools` when the
    # system prompt above it varies does not.
    if "messages" in cached_parts and "system" not in cached_parts and \
            system is not None and len(source_of(system, source)) > 500:
        findings.append(Finding(
            "warning", file, node.lineno, "prefix-order",
            "a breakpoint inside messages, but the larger system prompt above "
            "it is not cached",
            "The prefix runs tools → system → messages. Caching a later "
            "segment leaves everything before it paid for in full on every "
            "call."))

    # --- volatile content inside a cached prefix ---
    for name, value in (("tools", tools), ("system", system)):
        if value is None or not has_cache_control(value):
            continue
        text = source_of(value, source)
        match = VOLATILE.search(text)
        if match:
            findings.append(Finding(
                "error", file, node.lineno, "volatile-prefix",
                f"cached {name} contains {match.group(0)!r}, which changes "
                f"between calls",
                "A cached prefix must be byte identical every time. One "
                "varying value means the cache is written and never read — "
                "you pay the write premium on every request and get nothing."))

    # --- cached prefix that is probably too short ---
    if system is not None and has_cache_control(system):
        known = literal_length(system)
        if known is not None and 0 < known < 600:
            findings.append(Finding(
                "warning", file, node.lineno, "short-prefix",
                f"cached system prompt is only about {known} characters",
                f"A prefix under the model's minimum is not stored at all, "
                f"and no error says so — the breakpoint is simply inert. Most "
                f"models sit at {MIN_TOKENS_HINT} tokens; the range across "
                f"models runs from 512 to 4,096, so check the one you call. "
                f"Then check `cache_creation_input_tokens`."))

    # --- a breakpoint on a message that varies ---
    # A breakpoint on the newest message is the normal pattern for a growing
    # conversation: everything before it is unchanged, so the next request
    # still hits. It only fails when that block itself varies per request,
    # which is the same fault as a volatile system prompt.
    if messages is not None and has_cache_control(messages):
        text = source_of(messages, source)
        match = VOLATILE.search(text)
        if match:
            findings.append(Finding(
                "error", file, node.lineno, "volatile-breakpoint",
                f"the cached message block contains {match.group(0)!r}, which "
                f"changes between calls",
                "The hash at that breakpoint differs every request, so the "
                "lookback finds nothing and you pay the write premium each "
                "time. Put the breakpoint at the end of the part that does "
                "not change, and let the varying text follow it."))



# --- request shapes that fail, or quietly do nothing ---

THINKING_MIN_BUDGET = 1024

# Levels `effort` takes. Present here only to recognise the value when it has
# been put in the wrong place.
EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}


def literal_int(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def dict_entry(node, key):
    """The value for `key` in a dict literal, or None."""
    if not isinstance(node, ast.Dict):
        return None
    for name, value in zip(node.keys, node.values):
        if isinstance(name, ast.Constant) and name.value == key:
            return value
    return None


def check_thinking(node, file, source, findings):
    thinking = keyword(node, "thinking")
    if thinking is None:
        return

    if keyword(node, "temperature") is not None:
        findings.append(Finding(
            "error", file, node.lineno, "thinking-with-temperature",
            "extended thinking and `temperature` in the same request",
            "The API rejects the pair. Drop temperature: with thinking on, "
            "the reasoning is where the variation lives."))

    messages = keyword(node, "messages")
    if messages is not None:
        text = source_of(messages, source)
        if re.search(r"['\"]role['\"]\s*:\s*['\"]assistant['\"]", text) and \
                text.rstrip().endswith("]"):
            findings.append(Finding(
                "warning", file, node.lineno, "thinking-with-prefill",
                "extended thinking with what looks like a prefilled "
                "assistant turn",
                "Thinking does not work with a prefill. If the last message "
                "here is a partial assistant turn, drop it and ask for the "
                "format in the prompt instead."))

    budget = dict_entry(thinking, "budget_tokens") or dict_entry(thinking, "budget")
    value = literal_int(budget) if budget is not None else None
    if value is not None:
        if value < THINKING_MIN_BUDGET:
            findings.append(Finding(
                "error", file, node.lineno, "thinking-budget-too-small",
                f"thinking budget of {value} tokens, under the "
                f"{THINKING_MIN_BUDGET} minimum",
                "The request is rejected. Raise it, and raise max_tokens with "
                "it."))
        limit = literal_int(keyword(node, "max_tokens"))
        if limit is not None and value >= limit:
            findings.append(Finding(
                "error", file, node.lineno, "thinking-budget-over-max",
                f"thinking budget {value} is not below max_tokens {limit}",
                "The budget comes out of max_tokens, so the answer would have "
                "nothing left. Give max_tokens room above the budget."))

    misplaced = dict_entry(thinking, "effort")
    if misplaced is not None:
        findings.append(Finding(
            "error", file, node.lineno, "effort-in-thinking",
            "`effort` inside `thinking`",
            "It belongs in `output_config`. Where it is, it is an unknown key "
            "in the thinking object."))


# Shapes a model rejects although an earlier model in its line took them.
# Keyed by the id as the request names it; a Bedrock `anthropic.` prefix is
# dropped first. An unknown or computed model is not judged.
BUDGET_REMOVED = {"claude-fable-5-1", "claude-fable-5", "claude-opus-5-5",
                  "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7",
                  "claude-sonnet-5-5", "claude-sonnet-5"}
NO_DISABLED_THINKING = {
    "claude-sonnet-5-5": "To turn thinking off on Sonnet 5.5, send "
                         "thinking={\"type\": \"between_tools\"} at effort "
                         "high or below, or keep it on at a low effort.",
    "claude-opus-5-5": "Thinking cannot be turned off on Opus 5.5. Omit "
                       "`thinking` and lower `effort` instead.",
    "claude-fable-5-1": "Thinking is always on. Omit `thinking`.",
    "claude-fable-5": "Thinking is always on. Omit `thinking`.",
}
NO_FORCED_TOOL = {"claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"}
BETWEEN_TOOLS_MODELS = {"claude-sonnet-5-5"}
BETWEEN_TOOLS_EFFORT = {"low", "medium", "high"}


def literal_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def model_of(node):
    model = literal_str(keyword(node, "model"))
    if model and model.startswith("anthropic."):
        model = model[len("anthropic."):]
    return model


def check_model_shapes(node, file, findings):
    model = model_of(node)
    if model is None:
        return
    thinking = keyword(node, "thinking")
    kind = literal_str(dict_entry(thinking, "type"))

    if model in BUDGET_REMOVED and (
            kind == "enabled" or dict_entry(thinking, "budget_tokens") is not None):
        findings.append(Finding(
            "error", file, node.lineno, "thinking-budget-removed",
            f"a fixed thinking budget on {model}",
            "This model rejects `budget_tokens` with a 400. Use "
            "thinking={\"type\": \"adaptive\"} and set the depth with "
            "output_config={\"effort\": ...}."))

    if kind == "disabled" and model in NO_DISABLED_THINKING:
        findings.append(Finding(
            "error", file, node.lineno, "thinking-disabled-rejected",
            f"thinking={{\"type\": \"disabled\"}} on {model}",
            "The request is rejected with a 400. "
            + NO_DISABLED_THINKING[model]))

    if kind == "between_tools":
        effort = literal_str(dict_entry(keyword(node, "output_config"), "effort"))
        if model not in BETWEEN_TOOLS_MODELS:
            findings.append(Finding(
                "error", file, node.lineno, "between-tools-unsupported",
                f"thinking type `between_tools` on {model}",
                "Only Claude Sonnet 5.5 accepts it. On this model, lower "
                "`effort` instead."))
        elif effort is not None and effort not in BETWEEN_TOOLS_EFFORT:
            findings.append(Finding(
                "error", file, node.lineno, "between-tools-effort",
                f"`between_tools` with effort {effort!r}",
                "It is accepted only at effort high or below. Lower the "
                "effort, or turn thinking back on."))
        if thinking is not None and len(getattr(thinking, "keys", [])) > 1:
            findings.append(Finding(
                "error", file, node.lineno, "between-tools-extra-field",
                "`between_tools` with another field in `thinking`",
                "It takes no other field: `display` or `budget_tokens` next "
                "to it is a 400."))

    choice = literal_str(dict_entry(keyword(node, "tool_choice"), "type"))
    if choice in {"any", "tool"} and model in NO_FORCED_TOOL:
        findings.append(Finding(
            "error", file, node.lineno, "forced-tool-choice-rejected",
            f"tool_choice of type {choice!r} on {model}",
            "Forced tool use is rejected with a 400. Use "
            "tool_choice={\"type\": \"auto\"} and name the tool in the "
            "prompt, with `strict: true` on it; or ask for structured output "
            "with output_config={\"format\": ...} if the call only existed "
            "to get JSON back."))


def check_effort(node, file, findings):
    effort = keyword(node, "effort")
    if effort is None:
        return
    level = effort.value if isinstance(effort, ast.Constant) else None
    named = f" ({level!r})" if level in EFFORT_LEVELS else ""
    findings.append(Finding(
        "error", file, node.lineno, "effort-top-level",
        f"`effort`{named} passed as its own argument",
        "It goes inside `output_config`: output_config={\"effort\": "
        "\"high\"}. On its own it is an unexpected keyword."))


def check_system(node, file, findings):
    system = keyword(node, "system")
    if isinstance(system, ast.Constant) and system.value is None:
        findings.append(Finding(
            "error", file, node.lineno, "system-none",
            "`system=None`",
            "The API does not accept a null system prompt — it is an error, "
            "not an omission. Build the arguments and add `system` only when "
            "there is one."))


def check_tool_results(tree, file, source, findings):
    """A tool that raised still owes the model a result."""
    if "tool_use" not in source or "tool_result" not in source:
        return
    if "is_error" in source:
        return
    guarded = any(isinstance(node, (ast.Try, ast.ExceptHandler))
                  for node in ast.walk(tree))
    findings.append(Finding(
        "warning", file, 0, "tool-errors-unreported",
        "a tool loop that never returns `is_error`",
        "Every tool_use needs a tool_result, including the ones that failed: "
        + ("the exception is caught, but the model is told nothing about it, "
           if guarded else
           "an exception here leaves the call unanswered, ")
        + "so the model either waits or invents what the tool returned. "
          "Return the message with is_error=True."))

def check_usage_reporting(tree, file, source, findings):
    """Caching that nobody measures is caching nobody knows is broken."""
    dumped = ast.dump(tree)
    if "cache_control" not in dumped:
        return
    if "cache_read_input_tokens" not in source and \
            "cache_creation_input_tokens" not in source:
        findings.append(Finding(
            "info", file, 0, "unverified-caching",
            "cache_control is used but usage is never read",
            "`cache_read_input_tokens` is the only proof a cache hit "
            "happened. Log it once — a silently missing cache looks exactly "
            "like a working one."))


def check_module(path, findings):
    file = path.name
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        findings.append(Finding("error", file, error.lineno or 0, "syntax",
                                f"cannot parse: {error.msg}", ""))
        return 0
    except Exception:
        return 0

    calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_messages_create(node):
            calls += 1
            check_call(node, file, source, findings)
            check_thinking(node, file, source, findings)
            check_effort(node, file, findings)
            check_model_shapes(node, file, findings)
            check_system(node, file, findings)

    if calls:
        check_usage_reporting(tree, file, source, findings)
        check_tool_results(tree, file, source, findings)
    return calls


def collect(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = collect(args.paths)
    findings, calls = [], 0
    for path in files:
        calls += check_module(path, findings)

    errors = [f for f in findings if f.level == "error"]

    if args.json:
        print(json.dumps({
            "files": len(files), "calls": calls, "errors": len(errors),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
        return 1 if errors else 0

    if not files:
        print("No Python files found.")
        return 0
    if not calls:
        print("No Claude API calls found.")
        return 0

    order = {"error": 0, "warning": 1, "info": 2}
    for finding in sorted(findings, key=lambda f: (order[f.level], f.file, f.line)):
        mark = {"error": "ERROR", "warning": "warn ", "info": "note "}[finding.level]
        where = f"{finding.file}:{finding.line}" if finding.line else finding.file
        print(f"{mark}  {where}  [{finding.rule}]")
        print(f"        {finding.message}")
        if finding.hint:
            print(f"        → {finding.hint}")

    print()
    if not findings:
        print(f"Clean — {calls} API call(s) across {len(files)} file(s).")
    else:
        print(f"{calls} API call(s): {len(errors)} error(s), "
              f"{len(findings) - len(errors)} to look at")

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
