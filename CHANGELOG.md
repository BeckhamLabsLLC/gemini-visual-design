# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-19

### Fixed
- **Image generation at the "final quality" tier was completely broken.** Google retired all Imagen 4 models on 2026-08-17, but `config.py` still pinned `imagen-4.0-generate-001`, so every `model="imagen"` call - and every `auto` call whose prompt mentioned "final", "production", or "hero image" - failed after three retries. Replaced by `gemini-3-pro-image`.
- **The MCP server would not start for anyone installing the plugin fresh.** `.mcp.json` relied on a `cwd` key that Claude Code ignores ([claude-code#17565](https://github.com/anthropics/claude-code/issues/17565)) to put `src/` on `sys.path`. Without a manual `pip install -e .`, the server died on `import mcp`. It now launches under `uv run`, which provisions dependencies automatically.
- **Template aspect ratios never reached the API.** All 25 templates declare an `aspect_ratio` and `resolution` (icons `1:1`, character sprites `9:16`, hero shots `16:9/2K`), and `enhance()` computed them and then discarded the result — so `template="icons/app-icon"` still produced a 16:9 image. Shape now resolves explicit argument → template → style profile → global default.
- **`aspect_ratio` was accepted and then silently ignored** on the default generation path, while still being recorded in metadata as though it had applied. Now wired through `GenerateContentConfig.image_config`, along with a new `resolution` parameter (1K/2K/4K).
- **Metadata lied about which model produced an asset.** Sidecars hardcoded `gemini-2.5-flash-image` regardless of what actually ran. They now record the model the server reports back.
- The project root is resolved from `CLAUDE_PROJECT_DIR`, not the unnamespaced `PROJECT_DIR` (which collides with common build tooling). Operations that write into your project refuse to run rather than silently targeting the plugin's own directory.
- Style-profile lookup stops at the repository boundary; a stray `.gemini-design-profile.json` in a parent directory or `$HOME` no longer leaks into unrelated projects.
- `analyze_design` runs on the text model instead of an image-generation model, and constrains output with a JSON schema instead of parsing prose out of a code fence. Critique no longer degrades to an unparsed blob when the model adds a preamble.
- Permanent API errors (400/404) are no longer retried; a bad model id fails in one call instead of three plus ~7s of backoff. Error classification uses typed SDK exceptions rather than substring matching, which previously read "401 bytes" in a message as an auth failure.
- Added an HTTP timeout, so a hung connection can no longer block a worker thread indefinitely.
- Video polling honours cancellation. `asyncio.to_thread` cannot interrupt a running thread, so an abandoned request previously kept a worker polling for the entire budget; the loop now waits on an event and stops within one poll interval.
- `save_asset` validates the destination before creating directories, constrains it to the project root, and refuses to overwrite an existing file.
- Preview writes are atomic; a crash mid-write no longer leaves truncated JSON that silently discards a style profile.
- Generated filenames use a random suffix instead of a per-process counter, so two servers can no longer overwrite each other's output.
- `create_profile` merges with an existing profile instead of rebuilding from defaults and discarding hand-edited fields.
- Dark-mode detection requires an actual `prefers-color-scheme: dark` rule; it previously matched any occurrence of the substring "dark", including `darkgray`.
- `list_generated` no longer drops assets whose sidecar lacks a `filename` key.
- `generate_design_tokens` reports `profile_updated` accurately, and surfaces a missing reference image instead of silently generating text-only tokens.
- An unknown tool name raises instead of returning an error payload shaped like a success.

- Image-to-video generation now correctly forwards the user's prompt alongside a reference image (was previously dropped, producing un-guided animations).
- `read_image` raises `ValueError` for unsupported file extensions instead of silently defaulting to `image/png` and producing cryptic Gemini API errors.
- `save_to_project` rejects filenames that would resolve outside the destination directory (path traversal guard).
- Video download return value is now validated to be `bytes`; non-bytes responses raise a clear `GeminiClientError` instead of writing garbage to disk.
- Internal `__version__` now matches the published package version (was 0.1.0, now 1.0.0).

### Added
- **Three image tiers** - `draft` (~$0.034/image), `fast` (~$0.067, default), `pro` (~$0.134, finals with legible text). `auto` picks `pro` for finals, else `fast`.
- **`resolution` parameter** (1K/2K/4K), clamped per tier.
- **Reference images work on every tier.** Previously a reference image forced the Gemini path because Imagen could not accept one.
- `veo-3.1-lite` video model (~$0.05/sec, half the price of `veo-3.1-fast`).
- Reference image support for style-consistent generation (commit `e299a42`).
- `.claude-plugin/marketplace.json`, so the plugin can be installed with `/plugin install`.
- `scripts/smoke_live.py` - an opt-in end-to-end test against the real API, with per-check cost estimates.
- Regression tests that fail if any configured model id is retired, is a `-preview` build, or is hardcoded outside `config.py`.
- Real coverage for the `call_tool` error map, which previously had none.
- `edit_image` now surfaces the model's commentary as `model_notes`, matching `generate_image`. It was being returned internally and dropped.

### Changed
- `model` values are now `draft`/`fast`/`pro`/`auto`. The old `gemini` and `imagen` names still work as aliases and emit a deprecation warning, but are no longer advertised in the tool schema.
- Quota, auth, and content-policy failures return distinct error types instead of collapsing into a single `api_error`.
- `count > 1` fans out to separate API calls - Gemini image models reject `candidate_count > 1`. Partial results are returned rather than discarded.
- Project CSS is scanned in a single pass with `node_modules` and friends excluded, off the event loop. It previously read every matching file twice, synchronously.
- Preview cleanup runs at most hourly instead of on every generation.
- Video polling defaults to a 10-minute budget (`GEMINI_VISUAL_VIDEO_TIMEOUT`) and retries transient failures mid-poll.
- MCP tool input schemas now declare `minLength` constraints on `prompt`, `instruction`, and `description` fields so invalid inputs are rejected at the protocol layer instead of wasting an API turn.
- Truly unexpected exceptions in the MCP `call_tool` handler now log a full traceback and propagate up to the framework instead of being silently wrapped as a generic error string.
- Server now logs a structured startup line with version, API key status (set/missing only — never the value), and the list of registered tools.

### Removed
- Imagen support. Google retired the models; `model="imagen"` now maps to `pro`.
- The unused `Pillow` dependency - nothing imported it.
- Dead duplicate `_retry_async` method in `gemini_client.py` (35 lines, never called — every code path uses `_sync_call` via `asyncio.to_thread`).
- Veo 2 models (commit `5033db3`), along with a repair to the polling loop.

## [1.0.0] - 2026-02-24

### Added
- Initial release of the Gemini Visual Design Claude Code plugin.
- **9 MCP tools**: `generate_image`, `edit_image`, `analyze_design`, `generate_video`, `save_asset`, `list_generated`, `generate_design_tokens`, `init_style_profile`, `get_prompt_templates`.
- **5 slash commands**: `/design-mockup`, `/create-asset`, `/create-video`, `/design-system`, `/review-visuals`.
- **`visual-enhancer` agent** that proactively suggests visual improvements after Claude writes UI code (HTML, JSX, TSX, Vue, Svelte, CSS).
- **`visual-design-system` skill** with prompt-engineering reference, model selection guide, and a template library across UI mockups, game assets, landing pages, and icons.
- **SessionStart hook** that validates `GEMINI_API_KEY` is set and points users to Google AI Studio if not.
- **Prompt enhancement pipeline** — every prompt passes through validation, template injection, and style-profile context before hitting the API.
- **Project-aware style profiles** (`.gemini-design-profile.json`) with auto-detection from Tailwind/CSS configs.
- **Draft-first workflow** — fast Gemini Flash for iterations, Imagen 4 for finals, Veo for video. *(Imagen was retired by Google in August 2026; see 1.1.0.)*
- **Edit-over-regenerate** philosophy with multi-turn image editing.
- **Generation history** with metadata sidecars and a 7-day auto-cleanup of the preview cache.

[Unreleased]: https://github.com/BeckhamLabsLLC/gemini-visual-design/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/BeckhamLabsLLC/gemini-visual-design/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/BeckhamLabsLLC/gemini-visual-design/releases/tag/v1.0.0
