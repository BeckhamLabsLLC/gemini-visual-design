# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Image-to-video generation now correctly forwards the user's prompt alongside a reference image (was previously dropped, producing un-guided animations).
- `read_image` raises `ValueError` for unsupported file extensions instead of silently defaulting to `image/png` and producing cryptic Gemini API errors.
- `save_to_project` rejects filenames that would resolve outside the destination directory (path traversal guard).
- Video download return value is now validated to be `bytes`; non-bytes responses raise a clear `GeminiClientError` instead of writing garbage to disk.
- Internal `__version__` now matches the published package version (was 0.1.0, now 1.0.0).

### Changed
- MCP tool input schemas now declare `minLength` constraints on `prompt`, `instruction`, and `description` fields so invalid inputs are rejected at the protocol layer instead of wasting an API turn.
- Truly unexpected exceptions in the MCP `call_tool` handler now log a full traceback and propagate up to the framework instead of being silently wrapped as a generic error string.
- Server now logs a structured startup line with version, API key status (set/missing only — never the value), and the list of registered tools.

### Removed
- Dead duplicate `_retry_async` method in `gemini_client.py` (35 lines, never called — every code path uses `_sync_call` via `asyncio.to_thread`).

## [1.0.0] - 2026-04-06

### Added
- Initial release of the Gemini Visual Design Claude Code plugin.
- **9 MCP tools**: `generate_image`, `edit_image`, `analyze_design`, `generate_video`, `save_asset`, `list_generated`, `generate_design_tokens`, `init_style_profile`, `get_prompt_templates`.
- **5 slash commands**: `/design-mockup`, `/create-asset`, `/create-video`, `/design-system`, `/review-visuals`.
- **`visual-enhancer` agent** that proactively suggests visual improvements after Claude writes UI code (HTML, JSX, TSX, Vue, Svelte, CSS).
- **`visual-design-system` skill** with prompt-engineering reference, model selection guide, and a template library across UI mockups, game assets, landing pages, and icons.
- **SessionStart hook** that validates `GEMINI_API_KEY` is set and points users to Google AI Studio if not.
- **Prompt enhancement pipeline** — every prompt passes through validation, template injection, and style-profile context before hitting the API.
- **Project-aware style profiles** (`.gemini-design-profile.json`) with auto-detection from Tailwind/CSS configs.
- **Draft-first workflow** — fast Gemini Flash for iterations, Imagen 4 for finals, Veo for video.
- **Edit-over-regenerate** philosophy with multi-turn image editing.
- **Generation history** with metadata sidecars and a 7-day auto-cleanup of the preview cache.

[Unreleased]: https://github.com/BeckhamLabsLLC/gemini-visual-design/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/BeckhamLabsLLC/gemini-visual-design/releases/tag/v1.0.0
