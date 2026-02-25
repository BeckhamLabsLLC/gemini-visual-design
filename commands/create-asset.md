---
name: create-asset
description: Generate visual assets (icons, textures, illustrations, backgrounds)
argument-hint: "[asset type and description]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__gemini-visual-design__generate_image
  - mcp__gemini-visual-design__edit_image
  - mcp__gemini-visual-design__save_asset
  - mcp__gemini-visual-design__get_prompt_templates
  - mcp__gemini-visual-design__list_generated
---

# Create Asset Command

Generate visual assets with style-profile consistency.

## Instructions

### 1. Load Style Profile
- Check for `.gemini-design-profile.json`
- If missing, note it and proceed — but mention the user should create one for consistency

### 2. Determine Asset Type
- If argument provided, parse the asset type from it
- If not, ask: "What type of asset? (icon, texture, illustration, background, sprite, logo concept)"
- Browse relevant templates with `get_prompt_templates`:
  - Icons → category: "icons"
  - Textures/sprites → category: "game-assets"
  - UI elements → category: "web-components"

### 3. Apply Template
- Suggest the most relevant template
- Let the user customize placeholder values
- Use their description as the primary input, template as structure

### 4. Generate
- Use `generate_image` with the appropriate model:
  - Drafts/exploration: model="gemini"
  - Production-quality final: model="imagen"
- For icon sets or variations: use count=4 with Imagen

### 5. Review and Edit
- Show the result path
- Ask for feedback
- Use `edit_image` for adjustments
- Iterate until satisfied

### 6. Save
- Use `save_asset` to save to the project
- Suggest a descriptive filename

## Output Format

After generation:
- File path for viewing
- Enhanced prompt used
- Model and template applied
- Suggestions for next steps (edit, generate variations, save)
