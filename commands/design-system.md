---
name: design-system
description: Generate design system tokens and style profile from description or reference
argument-hint: "[description or 'from image <path>']"
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__gemini-visual-design__generate_design_tokens
  - mcp__gemini-visual-design__init_style_profile
  - mcp__gemini-visual-design__generate_image
  - mcp__gemini-visual-design__save_asset
---

# Design System Command

Generate a design system with tokens, style profile, and optional visual previews.

## Instructions

### 1. Gather Requirements
- If argument provided, use it as the description
- If "from image <path>", use the image as a reference
- If no argument, ask about:
  - Brand mood (professional, playful, luxurious, technical, friendly)
  - Project type (game, landing-page, web-app)
  - Color preferences (any specific colors or "generate for me")
  - Output format preference (css, tailwind, json, scss)

### 2. Generate Design Tokens
- Use `generate_design_tokens` with the description
- If a reference image was provided, include it for color extraction
- Choose the format matching the project's tech stack

### 3. Present Tokens
- Show the generated code (CSS variables, Tailwind config, etc.)
- Highlight the color palette, typography scale, and spacing system

### 4. Create Style Profile
- Use `init_style_profile` to save the design system as a project profile
- This ensures all future generations use these tokens

### 5. Optional: Generate Visual Preview
- Offer to generate a visual preview using the new design system
- Use `generate_image` with a relevant template to show the tokens in action
- Example: Generate a dashboard mockup using the new color palette

### 6. Save
- Save the design tokens file to the project
- Confirm the style profile was created/updated

## Output Format

Present the design system as:
```
Design System Generated

Colors:
  Primary: #XXXX
  Secondary: #XXXX
  Background: #XXXX
  ...

Typography:
  Headings: [font]
  Body: [font]
  Scale: [sizes]

Spacing: [scale]

Tokens saved to: [path]
Style profile: [path]
```
