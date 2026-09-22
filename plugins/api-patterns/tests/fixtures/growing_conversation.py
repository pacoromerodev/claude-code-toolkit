"""A conversation that caches the way a conversation should.

The breakpoint sits on the newest turn, inline in the request: everything
before it is fixed, so the next request's prefix still matches. The second
call shows the other mode — one cache_control at the top level, which moves
the breakpoint forward on its own as the history grows.
"""
import anthropic

client = anthropic.Anthropic()

BRIEF = "You are a support agent for an airline. " * 80


def turn(history, question):
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{"type": "text", "text": BRIEF,
                 "cache_control": {"type": "ephemeral"}}],
        messages=history + [{
            "role": "user",
            "content": [{
                "type": "text",
                "text": question,
                "cache_control": {"type": "ephemeral"},
            }],
        }],
    )
    print(response.usage.cache_read_input_tokens)
    return response


def turn_automatic(history, question):
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{"type": "text", "text": BRIEF}],
        messages=history + [{"role": "user", "content": question}],
        cache_control={"type": "ephemeral"},
    )
    print(response.usage.cache_read_input_tokens)
    return response
