---
name: review-visuals
description: Analyze and critique design screenshots with actionable suggestions
argument-hint: "[path to screenshot or design image]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__gemini-visual-design__analyze_design
  - mcp__gemini-visual-design__edit_image
  - mcp__gemini-visual-design__save_asset
  - mcp__gemini-visual-design__list_generated
---

# Review Visuals Command

Analyze design screenshots and provide actionable improvement suggestions.

## Instructions

### 1. Get the Image
- If a path is provided as argument, use it directly
- If no path, ask the user for the screenshot/design image path
- Verify the file exists

### 2. Determine Context
- Ask about project type if not obvious: game, landing-page, web-app, or general
- Ask about focus area if the user has a specific concern: color, layout, typography, or overall

### 3. Analyze
- Use `analyze_design` with the appropriate focus and project_type
- Default to focus="overall" for comprehensive review

### 4. Present Results
- Show the scored categories clearly
- List issues ordered by severity (high → medium → low)
- For each issue, highlight the `edit_instruction` — these can be used directly with `edit_image`

### 5. Offer Improvements
- Ask if the user wants to apply any of the suggested fixes
- For each chosen fix, use `edit_image` with the issue's `edit_instruction`
- Show the result and ask for further edits

### 6. Iterate
- Re-analyze after edits to verify improvement
- Continue until the user is satisfied or decides to save

## Output Format

Present analysis as:
```
Score: X/10

Strengths:
- [what works well]

Issues:
1. [HIGH] Issue description
   Fix: [edit instruction]
2. [MEDIUM] Issue description
   Fix: [edit instruction]

Priority Improvements:
1. [most impactful change]
2. [next most impactful]
```
