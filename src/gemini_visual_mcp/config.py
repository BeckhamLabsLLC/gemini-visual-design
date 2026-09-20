"""Configuration for Gemini Visual Design MCP server."""

import os
from pathlib import Path

# API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# Model identifiers
#
# Only GA model ids belong here. Preview ids are retired on Google's own
# schedule with no warning in-band: this plugin previously pinned
# "imagen-4.0-generate-001" (shut down 2026-08-17) and
# "gemini-3.1-flash-image-preview" (announced shutdown 2026-06-25), both of
# which broke generation silently. tests/test_model_ids.py guards against a
# preview or retired id creeping back in.
# ---------------------------------------------------------------------------

# Image generation tiers, cheapest to best.
IMAGE_MODELS = {
    "draft": "gemini-3.1-flash-lite-image",  # fastest / cheapest iteration
    "fast": "gemini-3.1-flash-image",  # default
    "pro": "gemini-3-pro-image",  # finals; legible text, reference images
}
DEFAULT_IMAGE_TIER = "fast"

# Legacy tier names kept working for older transcripts and saved metadata.
# Deliberately NOT advertised in the tool schema enum - see resolve_image_tier.
IMAGE_MODEL_ALIASES = {
    "gemini": "fast",
    "flash": "fast",
    "imagen": "pro",  # Imagen 4 was retired; "pro" is its replacement
    "final": "pro",
    "lite": "draft",
}

# Highest resolution each tier will honor. Requests above this are clamped.
IMAGE_MODEL_MAX_RESOLUTION = {"draft": "1K", "fast": "2K", "pro": "4K"}

GEMINI_FLASH_TEXT = "gemini-2.5-flash"

VEO_3_MODEL = "veo-3.1-generate-preview"
VEO_3_FAST_MODEL = "veo-3.1-fast-generate-preview"
VEO_3_LITE_MODEL = "veo-3.1-lite-generate-preview"

# Default generation parameters
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1K"
DEFAULT_IMAGE_COUNT = 1
DEFAULT_VIDEO_DURATION = 4
DEFAULT_VIDEO_RESOLUTION = "720p"

# Networking
API_TIMEOUT_MS = 120_000
VIDEO_POLL_TIMEOUT_SECONDS = int(os.environ.get("GEMINI_VISUAL_VIDEO_TIMEOUT", "600"))

# Preview/cache directory
PREVIEW_DIR = Path.home() / ".cache" / "gemini-visual-design" / "preview"
PREVIEW_MAX_AGE_DAYS = 7

# Style profile filename
STYLE_PROFILE_FILENAME = ".gemini-design-profile.json"

# Prompt validation
MIN_PROMPT_LENGTH = 10

# Template categories
TEMPLATE_CATEGORIES = [
    "ui-mockups",
    "game-assets",
    "landing-pages",
    "web-components",
    "icons",
]

# Aspect ratios accepted by the Gemini image models.
ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"]

# Supported resolutions for images
IMAGE_RESOLUTIONS = ["1K", "2K", "4K"]

# Video durations
VIDEO_DURATIONS = [4, 6, 8]

# Video resolutions
VIDEO_RESOLUTIONS = ["720p", "1080p"]

# Model selection labels
MODEL_CHOICES_IMAGE = ["draft", "fast", "pro", "auto"]
MODEL_CHOICES_VIDEO = ["veo-3.1", "veo-3.1-fast", "veo-3.1-lite"]

# Analysis focus areas
ANALYSIS_FOCUS_AREAS = ["color", "layout", "typography", "overall"]

# Project types
PROJECT_TYPES = ["game", "landing-page", "web-app", "general"]

# Design token formats
TOKEN_FORMATS = ["css", "tailwind", "json", "scss"]


def resolve_image_tier(value: str | None) -> tuple[str, str | None]:
    """Normalize a user-supplied image model name to a tier.

    Returns (tier, warning). Never raises: an unusable value falls back to the
    default tier with a warning rather than failing a call the user already
    framed. "auto" is passed through for the caller to resolve.
    """
    if not value:
        return DEFAULT_IMAGE_TIER, None

    key = value.strip().lower()
    if key == "auto" or key in IMAGE_MODELS:
        return key, None

    if key in IMAGE_MODEL_ALIASES:
        tier = IMAGE_MODEL_ALIASES[key]
        return tier, (
            f"model={value!r} is a legacy name and will be removed in a future "
            f"release; using {tier!r} instead."
        )

    return DEFAULT_IMAGE_TIER, (
        f"Unknown model {value!r}; falling back to {DEFAULT_IMAGE_TIER!r}. "
        f"Valid choices: {', '.join(MODEL_CHOICES_IMAGE)}."
    )


def clamp_resolution(tier: str, resolution: str | None) -> tuple[str, str | None]:
    """Clamp a requested resolution to what the tier supports.

    Returns (resolution, warning). Asking for 4K on a draft-tier model should
    still produce an image, just a smaller one.
    """
    requested = resolution or DEFAULT_RESOLUTION
    if requested not in IMAGE_RESOLUTIONS:
        return DEFAULT_RESOLUTION, (
            f"Unknown resolution {resolution!r}; using {DEFAULT_RESOLUTION}."
        )

    ceiling = IMAGE_MODEL_MAX_RESOLUTION.get(tier, DEFAULT_RESOLUTION)
    if IMAGE_RESOLUTIONS.index(requested) > IMAGE_RESOLUTIONS.index(ceiling):
        return ceiling, (f"{requested} is above what the {tier!r} tier supports; using {ceiling}.")
    return requested, None
