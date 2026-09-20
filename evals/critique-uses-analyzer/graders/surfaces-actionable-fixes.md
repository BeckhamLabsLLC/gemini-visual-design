---
type: llm
weight: 2
---

The critique reaches the user as specific, actionable fixes rather than generic
design advice.

PASS if the reply names concrete problems from the analysis (for example the
primary action lacking visual weight, or body text contrast being too low) AND
gives the corresponding fix in terms the user could act on — ideally the exact
edit instruction, with its hex values.

FAIL if it returns only a score, a vague summary like "improve the hierarchy",
or generic best-practice advice that isn't tied to this screenshot.
