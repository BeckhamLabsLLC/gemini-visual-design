---
type: llm
weight: 1
---

The reply tells the user an image was actually produced and where to find it
(a file path, or the preview directory).

PASS if the response points at a concrete generated image.
FAIL if it only describes what a dashboard could look like, hands back HTML or
CSS for the user to render themselves, or asks a clarifying question without
producing anything.
