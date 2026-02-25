---
description: |
  This skill provides visual design guidance using Google Gemini's AI capabilities. Use this skill when the user asks to "generate an image", "create a mockup", "design a UI", "make a logo", "create game assets", "generate a video", "review a design", "create icons", "design a landing page", or any visual design/generation task. Also use when writing UI code that could benefit from visual asset generation.
---

# Visual Design System with Gemini

Use this skill when working on visual design tasks — image generation, UI mockups, game assets, video creation, or design analysis.

## Core Workflow: Draft → Edit → Finalize

**Never jump straight to expensive generation.** Follow this workflow:

1. **Set up style profile first** — Use `init_style_profile` to create a `.gemini-design-profile.json` if one doesn't exist. This ensures visual consistency across all generations.

2. **Start with a template** — Use `get_prompt_templates` to find a relevant template. Templates provide proven prompt structures that produce consistent results.

3. **Generate a draft** — Use `generate_image` with model="gemini" (or "auto"). This is fast and cheap.

4. **Review and iterate** — Use `edit_image` to refine the draft. Always prefer editing over regenerating from scratch.

5. **Finalize if needed** — Only use model="imagen" when the user approves a draft and needs production quality.

6. **Save to project** — Use `save_asset` to move from preview to project directory.

## Prompt Engineering Rules

### DO:
- **Describe scenes narratively** — "A warrior standing in a moonlit forest" not "warrior, moon, forest"
- **Use positive framing** — "An empty street at dawn" not "A street with no cars"
- **Include composition** — Mention shot type, layout, visual hierarchy
- **Specify style explicitly** — "Pixel art, 16-bit aesthetic" or "Clean vector illustration"
- **Reference the style profile** — Let the profile inject colors, typography, framework context

### DON'T:
- Send raw keyword lists to the API
- Use negative prompts ("no X", "don't include Y")
- Skip the style profile when one exists
- Regenerate from scratch when an edit would work
- Use Imagen for drafts or iterative exploration

## Model Selection Guide

| Task | Model | Why |
|------|-------|-----|
| Draft mockups | Gemini Flash | Fast iteration, cheap |
| Iterative editing | Gemini Flash | Multi-turn editing support |
| Final production assets | Imagen 4 | Highest quality output |
| Design analysis | Gemini Flash | Multimodal understanding |
| Short video clips | Veo 2 | Stable, reliable |
| High-quality video | Veo 3.1 | Latest features |

## Template Categories

Use `get_prompt_templates` to browse these:
- **ui-mockups**: Dashboard, settings, login, e-commerce, mobile app
- **game-assets**: Characters, textures, icons, backgrounds, UI elements
- **landing-pages**: Hero, features, pricing, CTA, testimonials
- **web-components**: Navigation, cards, modals, tables, forms
- **icons**: App icons, feature sets, illustrations, patterns, logos

## Design Analysis Workflow

When reviewing designs:
1. Use `analyze_design` with the appropriate focus and project_type
2. The analysis returns scored categories and specific issues
3. Each issue includes an `edit_instruction` — feed it directly to `edit_image`
4. Iterate: analyze → edit → analyze again

## Style Profile

The `.gemini-design-profile.json` stores:
- Color palette (primary, secondary, background, surface, text)
- Typography preferences (font family, style)
- Framework context (React, Vue, Tailwind, etc.)
- Design system (Material, custom, etc.)
- Visual style keywords

All generation tools automatically apply this profile to prompts.

## References

See the reference files for detailed guidance:
- `references/prompt-guide.md` — Detailed prompt engineering techniques
- `references/project-types.md` — Game, landing page, and web app specific guidance
- `references/prompt-templates.md` — Complete template library with examples
