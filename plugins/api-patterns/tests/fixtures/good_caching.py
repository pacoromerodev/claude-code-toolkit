"""Caching done so it actually hits."""
import anthropic

client = anthropic.Anthropic()

# Static, long, identical on every call: the whole point of a cached prefix.
AGENT_BRIEF = "You are a support agent for an airline. " * 80

TOOLS = [
    {
        "name": "lookup_booking",
        "description": (
            "Look up a booking by its reference. Use when the customer gives "
            "a booking reference and you need the itinerary, passengers or "
            "status. Returns the booking as JSON, or raises NotFound when the "
            "reference does not exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string",
                              "description": "Six-character booking reference"}
            },
            "required": ["reference"],
        },
    }
]


def ask(question: str, today: str):
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        tools=TOOLS,
        system=[{
            "type": "text",
            "text": AGENT_BRIEF,
            "cache_control": {"type": "ephemeral"},
        }],
        # Everything that varies lives after the breakpoint.
        messages=[{"role": "user", "content": f"Today is {today}. {question}"}],
    )
    # The only proof a cache hit happened.
    print(response.usage.cache_read_input_tokens)
    return response
