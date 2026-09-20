---
description: A refinement must edit the existing asset, not regenerate from scratch.
tags: [core, editing]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: Claude calls edit_image on the existing path and never calls generate_image.
---

You just generated this dashboard mockup for me:

    /home/user/.cache/gemini-visual-design/preview/gen_20260919_120000_a1b2c3d4.png

It's close. The background is too light — make it darker, and leave everything
else exactly as it is.
