"""The same calls, shaped the way the API accepts."""
import anthropic

client = anthropic.Anthropic()


def think_hard(question):
    """Thinking: no temperature, budget above the floor and below max_tokens."""
    return client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 4000},
        messages=[{"role": "user", "content": question}],
    )


def think_adaptively(question):
    """Adaptive thinking: depth comes from effort, inside output_config."""
    return client.messages.create(
        model="claude-opus-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": question}],
    )


def no_thinking(question):
    """Sonnet 5.5 turns thinking off with between_tools, at high or below."""
    return client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=1000,
        thinking={"type": "between_tools"},
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": question}],
    )


def must_classify(question, tools):
    """No forced tool on Sonnet 5.5: auto, with the tool named in the prompt."""
    return client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=1000,
        tools=tools,
        tool_choice={"type": "auto"},
        messages=[{"role": "user",
                   "content": f"Call the classify tool on this: {question}"}],
    )


def chat(messages, system=None):
    """system is added only when there is one — never passed as None."""
    params = {
        "model": "claude-sonnet-5",
        "max_tokens": 1000,
        "messages": messages,
    }
    if system:
        params["system"] = system
    return client.messages.create(**params)


def run_tools(response, tools):
    """Every tool_use gets a tool_result, including the ones that raised."""
    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        try:
            output = tools[block.name](**block.input)
            content, failed = str(output), False
        except Exception as error:
            content, failed = f"Error: {error}", True
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": content,
            "is_error": failed,
        })
    return results
