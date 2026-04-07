# Screenshots

These images are referenced from the top-level `README.md`. Every one is a real, unretouched output from the plugin's own MCP tools — reproducible from the prompt shown in its caption in the main README.

## Current files

| File | What it is | Source |
|---|---|---|
| `hero-dashboard.jpg` | The hero dashboard mockup at the top of the README | `mcp__gemini-visual-design__generate_image` with `model: gemini`, `aspect_ratio: 16:9` |
| `icon-set.jpg` | 6-icon project management icon grid | `generate_image` with `aspect_ratio: 3:4` |
| `edit-before.jpg` | Sneaker on beige (pre-edit) | `generate_image` with `aspect_ratio: 1:1` |
| `edit-after.jpg` | Same sneaker, deep purple background (post-edit) | `edit_image` against `edit-before.jpg` |
| `hero-dashboard.analysis.json` | Full design critique JSON | `analyze_design` against `hero-dashboard.jpg` with `focus: overall`, `project_type: web-app` |

## How to regenerate

1. Make sure `GEMINI_API_KEY` is set and the project has billing enabled (free tier currently has `limit: 0` for image generation models).
2. Restart Claude Code so the MCP server picks up `src/gemini_visual_mcp/config.py`.
3. From inside this plugin's directory, ask Claude to call the MCP tools listed in the "Source" column above with the prompts shown in the main README's gallery captions.
4. After each `generate_image`, call `save_asset` with `destination_dir=docs/screenshots` and the filename in the table above.

The captions in the top-level README always state the exact prompt used, so the gallery doubles as a working set of usage examples — anyone reading the README can copy a prompt and reproduce the exact image themselves.
