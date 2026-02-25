# Gemini Visual Design Plugin

## Environment Setup

```bash
pip install -e ".[dev]"
export GEMINI_API_KEY="your-key"
```

## Architecture

MCP server (`src/gemini_visual_mcp/`) with these modules:

| Module | Purpose |
|--------|---------|
| `server.py` | MCP server — tool registration, routing, error handling |
| `gemini_client.py` | Google GenAI SDK wrapper — auth, retry, all API calls |
| `config.py` | Constants — model IDs, defaults, enums |
| `prompt_engine.py` | Prompt validation, templates, enhancement pipeline |
| `style_profile.py` | Per-project `.gemini-design-profile.json` management |
| `image_gen.py` | Image generation with auto model selection (Gemini/Imagen) |
| `image_edit.py` | Image editing via multi-turn Gemini |
| `image_utils.py` | Shared image file reading and MIME detection |
| `analyzer.py` | Design analysis with structured JSON critique |
| `video_gen.py` | Video generation via Veo with async polling |
| `asset_manager.py` | Preview directory, metadata sidecars, save-to-project |

## Conventions

- **Prompt engine**: Every user prompt passes through `enhance()` before hitting the API — validates, applies templates, injects style profile context, adds structural hints
- **Style profiles**: `.gemini-design-profile.json` in project root stores colors, typography, framework info — all generation inherits these settings
- **Preview directory**: Generated assets land in `~/.cache/gemini-visual-design/preview/` with `.meta.json` sidecars. Use `save_asset` to copy to the project
- **Model selection**: Gemini Flash for fast drafts, Imagen 4 for final assets, Veo for video. `auto` mode selects based on prompt keywords
- **Edit over regenerate**: Always prefer `edit_image` over regenerating from scratch — builds on previous results

## Running Tests

```bash
pytest tests/ -v
ruff check src/ tests/
```
