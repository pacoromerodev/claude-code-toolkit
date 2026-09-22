"""Request shapes the API rejects, or that quietly do nothing."""
import anthropic

client = anthropic.Anthropic()

BRIEF = "You classify support tickets. " * 60


def think_hard(question):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2000,
        temperature=0.2,
        thinking={"type": "enabled", "budget_tokens": 512},
        messages=[{"role": "user", "content": question}],
    )


def think_over_budget(question):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        thinking={"type": "enabled", "budget_tokens": 4000},
        messages=[{"role": "user", "content": question}],
    )


def misplaced_effort(question):
    return client.messages.create(
        model="claude-opus-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        effort="high",
        messages=[{"role": "user", "content": question}],
    )


def effort_inside_thinking(question):
    return client.messages.create(
        model="claude-opus-5",
        max_tokens=16000,
        thinking={"type": "adaptive", "effort": "max"},
        messages=[{"role": "user", "content": question}],
    )


def chat(messages, system=None):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1000,
        system=None,
        messages=messages,
    )


def run_tools(response, tools):
    """Runs each tool_use block and builds the tool_result blocks."""
    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        try:
            output = tools[block.name](**block.input)
        except Exception:
            continue
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results
