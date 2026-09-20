---
type: llm
weight: 2
---

The user asked for a darker version of an image that already exists.

PASS if the reply hands back a revised image — a new file path for the edited
version — while making clear the original is untouched.

FAIL if it only describes how to darken the image, gives the user CSS or a
command to run themselves, says it cannot access the file, or starts a fresh
unrelated generation instead of revising the one named.
