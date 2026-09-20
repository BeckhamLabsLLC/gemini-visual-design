---
description: A design critique request should run analyze_design and surface its edit instructions.
tags: [core, analysis]
max_turns: 14
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: Claude calls analyze_design and passes the concrete edit instructions back to the user.
---

Take another look at the dashboard mockup you generated for me earlier — it
should be the most recent thing in the preview directory.

Tell me what's weakest about it, and be specific about how to fix it.
