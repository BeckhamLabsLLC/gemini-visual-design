# Prompt Engineering Guide for Gemini Visual Design

## Scene Description Format

Structure prompts as scene descriptions, not keyword lists:

```
[COMPOSITION]: Shot type, camera angle, framing
[SUBJECT]: Main element with specific details
[ENVIRONMENT]: Setting, background, context
[STYLE]: Art style, rendering technique, medium
[LIGHTING]: Light source, mood, time of day
[TECHNICAL]: Resolution, aspect ratio, color space
```

### Example — Bad vs Good

**Bad**: "dashboard, dark mode, charts, sidebar, modern"

**Good**: "A professional dark-themed analytics dashboard UI mockup. The layout features a narrow sidebar navigation with icons on the left, a top header bar with search and user avatar, and a main content area. The content area shows four KPI metric cards across the top row, a large area chart in the center, and a sortable data table below. Color scheme uses deep navy (#0f172a) background with electric blue (#3b82f6) accent highlights. Clean, modern interface with consistent 8px spacing grid."

## Photographic Language

Use photography terminology for realistic or semi-realistic images:

- **Shot types**: Close-up, medium shot, wide angle, bird's eye view, isometric
- **Lens effects**: Shallow depth of field, tilt-shift, fisheye, telephoto compression
- **Lighting setups**: Soft diffused light, dramatic side lighting, golden hour, studio lighting, rim light
- **Film styles**: Cinematic, editorial, lifestyle photography, product photography

## Text Rendering

Gemini can render text in images. For best results:

- Specify the exact text in quotes: `The text "Welcome Back" in bold sans-serif`
- Describe placement: "centered at the top of the card"
- Describe style: "white text with subtle drop shadow on dark background"
- Keep text short — longer text is more likely to have errors

## Consistency Across Generations

To maintain visual consistency:

1. **Establish a character/element in the first prompt** with full details
2. **Reference those details in follow-up prompts**: "The same warrior character from before, now..."
3. **Use the style profile** — it automatically injects consistent colors and style
4. **Use templates** — they enforce consistent structure across similar assets
5. **Edit instead of regenerate** — editing preserves established elements

## Positive Framing

AI models respond better to positive descriptions than negative exclusions.

| Instead of... | Say... |
|---------------|--------|
| "No people" | "An empty room" or "A deserted street" |
| "Not blurry" | "Sharp, crisp details" |
| "No text" | "Clean, text-free design" |
| "Don't make it dark" | "Bright, well-lit scene" |
| "Remove the watermark" | "Clean image without overlays" |

## Aspect Ratio Selection

- **16:9** — Dashboards, landing pages, hero images, video frames
- **9:16** — Mobile app screens, stories, vertical video
- **1:1** — Icons, avatars, app icons, textures, logos
- **4:3** — Traditional web layouts, presentation slides
- **3:4** — Portrait cards, profile images, vertical compositions

## Model-Specific Tips

### Gemini 2.5 Flash (Image Generation)
- Best for iterative work — supports multi-turn editing
- Good at understanding and modifying UI layouts
- Can handle text rendering reasonably well
- Use for all drafts and explorations

### Imagen 4
- Highest photorealistic quality
- Best for final production assets
- Excellent at textures, patterns, and photographic styles
- Does not support multi-turn editing — plan your prompt carefully
- Supports up to 4 images per request for variation

### Veo (Video)
- Describe motion and action, not just a static scene
- Include temporal information: "Camera slowly pans right...", "The sun sets over..."
- Keep descriptions focused — one main action or transition
- Reference images help establish the starting frame
