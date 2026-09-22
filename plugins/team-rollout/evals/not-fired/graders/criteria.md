---
type: llm
weight: 1
---

A short factual answer: Shift+Tab cycles the permission modes in the input
prompt. Mentioning the `--permission-mode` flag or the `defaultMode` setting as
well is fine.

Score well when the response:
- Says Shift+Tab, in the first line or two
- Stays short: a one-line question deserves a short answer

Score badly if the response:
- Gives a different key (Tab alone, Ctrl+P, …) as the way to switch
- Starts planning a rollout, reviews settings files, or works through the five
  rollout decisions
