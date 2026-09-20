---
description: A mockup request should generate an image, not hand-written HTML.
tags: [core, generation]
max_turns: 12
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: Claude calls generate_image and reports where the asset landed.
---

I'm building a web app and I want to see what a dark analytics dashboard could
look like before I build it — sidebar navigation, a few KPI cards, and a chart.

Give me something I can look at.
