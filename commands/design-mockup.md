---
name: design-mockup
description: Interactive mockup generation workflow — draft, iterate, finalize
argument-hint: "[description of what to mock up]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__gemini-visual-design__generate_image
  - mcp__gemini-visual-design__edit_image
  - mcp__gemini-visual-design__save_asset
  - mcp__gemini-visual-design__init_style_profile
  - mcp__gemini-visual-design__get_prompt_templates
  - mcp__gemini-visual-design__list_generated
---

# Design Mockup Command

Generate UI mockups with an iterative draft-first workflow.

## Instructions

Follow this workflow strictly — it minimizes wasted API calls:

### 1. Check Style Profile
- Look for `.gemini-design-profile.json` in the project
- If missing, ask the user about their project type, colors, and framework
- Create one with `init_style_profile` (use `auto_detect: true` to scan existing config)

### 2. Understand the Request
- If an argument is provided, use it as the mockup description
- If no argument, ask what page/component to mock up
- Suggest a relevant template from `get_prompt_templates` (category: "ui-mockups" or "web-components")

### 3. Generate Draft
- Use `generate_image` with model="gemini" (fast, cheap draft)
- Apply the suggested template if the user agrees
- Show the user the file path and the enhanced prompt that was used

### 4. Iterate
- Ask the user for feedback on the draft
- Use `edit_image` for refinements — NEVER regenerate from scratch unless the draft is fundamentally wrong
- Each edit builds on the previous result
- Repeat until the user is satisfied

### 5. Finalize (Optional)
- Ask if the user wants a higher-quality version
- If yes, regenerate with model="imagen" using the refined prompt
- Show the final result

### 6. Save
- Use `save_asset` to save the approved version to the project
- Suggest an appropriate filename and directory

## Output Format

After each generation/edit, report:
- File path (so user can view it)
- Model used
- Any prompt warnings
- Next suggested action (edit, finalize, or save)
