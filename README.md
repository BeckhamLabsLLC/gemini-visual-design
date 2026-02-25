# Gemini Visual Design Plugin

A Claude Code plugin that integrates Google Gemini's visual AI capabilities into the development workflow. Generates images, edits designs, creates videos, and analyzes visual designs — all enhanced by a prompt engineering pipeline and project-aware style profiles to minimize wasted API calls.

## Setup

### 1. Get a Gemini API Key

Get your API key at [Google AI Studio](https://aistudio.google.com/apikey).

### 2. Set Environment Variable

```bash
export GEMINI_API_KEY="your-api-key-here"
```

### 3. Install Dependencies

```bash
cd gemini-visual-design
pip install -e .
```

### 4. Install as Claude Code Plugin

The plugin is automatically detected when placed in your plugins directory. The `.mcp.json` file configures the MCP server.

## Commands

| Command | Description |
|---------|-------------|
| `/design-mockup` | Interactive mockup generation — draft, iterate, finalize |
| `/create-asset` | Generate visual assets (icons, textures, illustrations) |
| `/create-video` | Generate short video clips from text or reference images |
| `/review-visuals` | Analyze design screenshots with actionable suggestions |
| `/design-system` | Generate design tokens and style profiles |

## MCP Tools

| Tool | Description |
|------|-------------|
| `generate_image` | Generate images with Gemini (drafts) or Imagen 4 (finals) |
| `edit_image` | Edit existing images with natural language instructions |
| `analyze_design` | Visual design critique with scored categories |
| `generate_video` | Generate video clips with Veo models |
| `save_asset` | Save generated assets from preview to project |
| `list_generated` | List all generated assets with metadata |
| `generate_design_tokens` | Generate CSS/Tailwind/JSON design tokens |
| `init_style_profile` | Create or update project style profile |
| `get_prompt_templates` | Browse available prompt templates |

## Style Profile

Create a `.gemini-design-profile.json` in your project root to maintain visual consistency:

```json
{
  "project_type": "web-app",
  "framework": "React + Tailwind CSS",
  "design_system": "custom",
  "colors": {
    "primary": "#3b82f6",
    "secondary": "#8b5cf6",
    "background": "#0f172a",
    "surface": "#1e293b",
    "text": "#f8fafc"
  },
  "typography": {
    "style": "modern sans-serif",
    "heading_font": "Inter",
    "body_font": "Inter"
  },
  "visual_style": "clean, minimal, dark mode",
  "default_aspect_ratio": "16:9",
  "default_resolution": "1K"
}
```

Use `init_style_profile` with `auto_detect: true` to auto-populate from existing Tailwind/CSS config.

## Anti-Waste Design

This plugin is designed to minimize wasted API calls:

1. **Prompt Enhancement** — Every prompt passes through validation and enrichment before hitting the API
2. **Style Profiles** — All generations inherit project-specific colors, typography, and style
3. **Templates** — Start from proven prompt structures instead of blank prompts
4. **Draft-First** — Default to fast/cheap Gemini Flash for drafts, escalate to Imagen for finals
5. **Edit > Regenerate** — Always prefer editing over regenerating from scratch
6. **Generation History** — Metadata sidecars track what worked for reuse

## File Locations

- **Preview directory**: `~/.cache/gemini-visual-design/preview/`
- **Style profile**: `.gemini-design-profile.json` (project root)
- **Metadata sidecars**: `{filename}.meta.json` alongside each generated file
- **Auto-cleanup**: Preview files older than 7 days are cleaned up automatically

## Examples

### Generate a UI mockup
```
/design-mockup A dark-themed analytics dashboard with sidebar navigation and KPI cards
```

### Create game assets
```
/create-asset A pixel art treasure chest icon for inventory UI, 32x32 style
```

### Generate a video clip
```
/create-video Slow dolly forward through a misty forest at dawn, soft volumetric lighting
```

### Review an existing design
```
/review-visuals path/to/screenshot.png
```

### Set up a design system
```
/design-system Modern SaaS design tokens with blue primary and dark mode
```

## Troubleshooting

**Missing API key**: Set `GEMINI_API_KEY` environment variable. Get one at [Google AI Studio](https://aistudio.google.com/apikey).

**Quota errors**: You've exceeded the Gemini API rate limit. Wait a moment and retry — the client has built-in exponential backoff for transient errors.

**Content policy blocks**: Gemini refused to generate the image. Rephrase your prompt to avoid content that violates Google's safety policies.

**Slow video generation**: Video generation with Veo takes 1-3 minutes. This is normal. The polling has a 5-minute timeout.

**Style mismatch**: Generated assets don't match your project's look. Run `init_style_profile` with `auto_detect: true` to scan your existing CSS/Tailwind config and create a matching style profile.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
