# Running the same prompt on Bedrock and Vertex

The model is the same. The request is not, and the differences are where an
eval written against one provider stops being comparable on another.

## Amazon Bedrock

Calls go through `boto3`, not the Anthropic SDK, and the shape is its own:

```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-west-2")
response = client.converse(
    modelId=MODEL_ID,
    system=[{"text": "You classify support tickets."}],
    messages=[{"role": "user", "content": [{"text": "…"}]}],
    inferenceConfig={"temperature": 0, "stopSequences": ["</answer>"]},
)
text = response["output"]["message"]["content"][0]["text"]
```

Four things to carry across:

- **`content` is always a list of parts**, in both directions. A message can
  mix text and images, and an assistant reply arrives the same way.
- **Generation settings live in `inferenceConfig`**, not beside `messages`.
  The system prompt is its own top-level `system`, a list of parts.
- **Streaming** is `converse_stream`, whose `stream` yields `messageStart`,
  then `contentBlockDelta` events carrying the text, then `contentBlockStop`,
  `messageStop` and `metadata`.
- **A prefilled assistant turn** works the same way: Claude continues from it
  without repeating it, so the two halves have to be joined afterwards.

### The error that wastes an afternoon

Not every model is hosted in every region. Ask for one that is not, and the
error says the model does not exist — which reads as a wrong id, a typo, or
missing access, and sends people to IAM.

The fix is a **cross-region inference profile**: an id that routes the request
to a region where the model is hosted. It is a different string from the
catalogue's model id, copied from the cross-region inference section of the
Bedrock console, and it goes in `modelId` unchanged.

### Tools

The schema is wrapped, and the result carries a status rather than a flag:

```python
tools = [{
    "toolSpec": {
        "name": "lookup_booking",
        "description": "…what it does, when to use it, what it returns…",
        "inputSchema": {"json": SCHEMA},
    }
}]

tool_choice = {"auto": {}}        # or {"any": {}}, or {"tool": {"name": "…"}}
```

A tool call comes back as a `toolUse` part with `toolUseId`, `name` and
`input`. The answer goes back as a `toolResult` part with the same
`toolUseId`, its content as parts, and `status` of `"success"` or `"error"` —
where the Anthropic API uses `is_error`. A failed tool still owes a result;
the id is what matches it to its call when several run at once.

## Google Vertex AI

The Anthropic SDK is used directly, through `AnthropicVertex`, so the request
body is the one you already know. What differs is access:

1. Enable the model in Model Garden, once per project.
2. Authenticate with the gcloud CLI, including
   `gcloud auth application-default login`.
3. The SDK picks those application default credentials up on its own. There
   is no API key: a missing credential looks like an authentication error, not
   a configuration one.

The client takes the region and the project, and both have to match where the
model was enabled.

## What this means for an eval

- **Record the provider with the score.** The same prompt, the same dataset
  and the same model can differ between providers, and a number with no
  provider beside it is not comparable to the next one.
- **Keep the request shape out of the grader.** Wrap the call so the dataset
  and the graders see one interface; otherwise porting an eval means
  rewriting the cases.
- **Fail loudly on a missing model.** A region that does not host it is the
  most common failure, and its message points somewhere else.
