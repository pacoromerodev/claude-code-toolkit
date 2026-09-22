"""The breakpoint sits on a block that is different on every request."""
from datetime import datetime

import anthropic

client = anthropic.Anthropic()

BRIEF = "You are a support agent for an airline. " * 80


def turn(history, question):
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{"type": "text", "text": BRIEF}],
        messages=history + [{
            "role": "user",
            "content": [{
                "type": "text",
                "text": f"Asked at {datetime.now()}: {question}",
                "cache_control": {"type": "ephemeral"},
            }],
        }],
    )
    print(response.usage.cache_read_input_tokens)
    return response
