---
type: llm
weight: 1
---

The reply reflects that the user asked to keep it cheap.

PASS if Claude either picks an explicitly cheaper tier (draft, or fast) or tells
the user what the cheaper option is and roughly what it costs.
FAIL if it silently uses the most expensive tier, or ignores the cost constraint
entirely.
