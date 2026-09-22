---
type: llm
weight: 1
---

Not every model is hosted in every region, and asking for one that is not
produces an error saying the model does not exist — which reads like a wrong
id or a permissions problem and sends people to IAM. The colleague in another
region working is the clue.

Score well when the response:
- Names regional availability as the cause, and connects it to the colleague
  in a different region
- Says the fix is a cross-region inference profile: a different id from the
  catalogue's, which routes the request to a region hosting the model
- Says where that id comes from — the cross-region inference section of the
  Bedrock console — and that it goes into `modelId` as it is
- Does not send the reader to IAM, quotas or model access requests as the
  first move, given both are already stated to be in place

Score badly when the response:
- Recommends checking IAM permissions or requesting model access
- Suggests retyping the model id, or a different model, with no reason
- Suggests switching region without saying that an inference profile does it
  without moving anything
