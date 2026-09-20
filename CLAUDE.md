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
| `image_gen.py` | Image generation with auto tier selection (draft/fast/pro) |
| `image_edit.py` | Image editing via multi-turn Gemini |
| `image_utils.py` | Shared image file reading and MIME detection |
| `analyzer.py` | Design analysis with structured JSON critique |
| `video_gen.py` | Video generation via Veo with async polling |
| `asset_manager.py` | Preview directory, metadata sidecars, save-to-project |

## Conventions

- **Prompt engine**: Every user prompt passes through `enhance()` before hitting the API — validates, applies templates, injects style profile context, adds structural hints
- **Style profiles**: `.gemini-design-profile.json` in project root stores colors, typography, framework info — all generation inherits these settings
- **Preview directory**: Generated assets land in `~/.cache/gemini-visual-design/preview/` with `.meta.json` sidecars. Use `save_asset` to copy to the project
- **Model selection**: three image tiers — `draft` (flash-lite), `fast` (flash, default), `pro` (Gemini 3 Pro Image, finals). `auto` picks `pro` for finals, else `fast`. Veo for video. Model IDs live only in `config.py`; `tests/test_model_ids.py` guards against preview/retired IDs
- **Edit over regenerate**: Always prefer `edit_image` over regenerating from scratch — builds on previous results

## Running Tests

```bash
pytest tests/ -v
ruff check src/ tests/ && ruff format --check src/ tests/
```

Four layers, each catching what the one above it structurally cannot:

| Command | Catches | Cost |
|---|---|---|
| `pytest tests/ -v` | Logic. Note most tests mock mcp's `Server`, so they cannot see a handler that was never registered — `tests/test_protocol.py` uses a real one | free |
| `python scripts/check_protocol.py` | The launch command, dependency resolution, and MCP wiring, by speaking stdio to the process `.mcp.json` actually starts | free |
| `python scripts/smoke_live.py` | Retired model IDs and whether `image_config` is really honored. Mocks cannot tell you Google deleted a model | ~$0.80 |
| `claude plugin eval .` | Whether Claude *reaches for* the tools, vs. just whether they work | ~$0.13/run |

Run `check_protocol.py` after touching `.mcp.json`, `server.py`, or dependencies;
`smoke_live.py` after touching model IDs or `gemini_client.py`.
