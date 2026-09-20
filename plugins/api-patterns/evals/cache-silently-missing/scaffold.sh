#!/usr/bin/env bash
set -euo pipefail
cat > agent.py <<'PY'
from datetime import datetime

import anthropic

client = anthropic.Anthropic()

BRIEF = "You are a support agent for an airline. " * 90


def answer(question: str):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": BRIEF + f" The current time is {datetime.now().isoformat()}.",
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": question}],
    )
PY
