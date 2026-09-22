---
type: llm
weight: 1
---

The agent file has four faults, and the symptom follows from the first: there
is no output format, so there is nothing to return and nothing to cut. The
body is a persona rather than a procedure, "be comprehensive" invites the
length being complained about, and a reviewer has been given Write and Edit.

Score well when the response:
- Names the missing output format as the main cause, and says a subagent
  returns only its summary, so the format is what it is
- Proposes a concrete format with fixed headings, including one for what the
  agent could not check
- Flags the persona opening as adding nothing, and "be comprehensive" as
  asking for exactly the sprawl reported
- Notices that a reviewing agent holds Write and Edit, and says why that is
  wrong: the fix lands in a context nobody sees
- Says the description gives the main thread nothing to delegate with — no
  situation, no statement of what to pass

Score badly when the response:
- Blames the model, suggests a different model, or suggests a lower
  temperature
- Only tells the user to ask for a shorter answer
- Rewrites the persona into a better persona
- Suggests more tools or a larger context
