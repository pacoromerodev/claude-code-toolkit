#!/usr/bin/env python3
"""Audit Claude API calls for prompt caching mistakes that cost money silently.

    python3 check_caching.py client.py
    python3 check_caching.py src/ --json

Caching fails quietly: a request with a breakpoint in the wrong place simply
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

    if calls:
        check_usage_reporting(tree, file, source, findings)
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
