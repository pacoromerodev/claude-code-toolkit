"""Caching configured in the ways that silently miss."""
from datetime import datetime

import anthropic

client = anthropic.Anthropic()


def with_timestamp(question: str):
    # The timestamp changes every call, so the prefix never matches and the
    # write premium is paid every time.
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": "You are a support agent for an airline. " * 60 +
                    f" Today is {datetime.now()}.",
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": question}],
    )


def too_many(question: str):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        tools=[
            {"name": "a", "cache_control": {"type": "ephemeral"}},
            {"name": "b", "cache_control": {"type": "ephemeral"}},
            {"name": "c", "cache_control": {"type": "ephemeral"}},
        ],
        system=[{"type": "text", "text": "x" * 3000,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": question,
                   "cache_control": {"type": "ephemeral"}}],
    )


def too_short(question: str):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{"type": "text", "text": "Be concise.",
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": question}],
    )
