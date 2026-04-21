"""Configuration for Gemini Visual Design MCP server."""

import os
from pathlib import Path

# API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Model identifiers
# Image generation: Gemini 3.1 Flash Image Preview ("Nano Banana 2") is the
# current high-efficiency production model as of April 2026. The older
# "gemini-2.5-flash-image" is still listed by Google but has been throttled to
# zero on the free tier on at least some accounts; switching to 3.1 unblocks
# generation and gives better quality.
GEMINI_FLASH_IMAGE = "gemini-3.1-flash-image-preview"
GEMINI_FLASH_TEXT = "gemini-2.5-flash"
IMAGEN_MODEL = "imagen-4.0-generate-001"
VEO_3_MODEL = "veo-3.1-generate-preview"
VEO_3_FAST_MODEL = "veo-3.1-fast-generate-preview"

# Default generation parameters
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1K"
DEFAULT_IMAGE_COUNT = 1
DEFAULT_VIDEO_DURATION = 4
DEFAULT_VIDEO_RESOLUTION = "720p"

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

# Supported aspect ratios
ASPECT_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]

# Supported resolutions for images
IMAGE_RESOLUTIONS = ["1K", "2K"]

# Video durations
VIDEO_DURATIONS = [4, 6, 8]

# Video resolutions
VIDEO_RESOLUTIONS = ["720p", "1080p"]

# Model selection labels
MODEL_CHOICES_IMAGE = ["gemini", "imagen", "auto"]
MODEL_CHOICES_VIDEO = ["veo-3.1", "veo-3.1-fast"]

# Analysis focus areas
ANALYSIS_FOCUS_AREAS = ["color", "layout", "typography", "overall"]

# Project types
PROJECT_TYPES = ["game", "landing-page", "web-app", "general"]

# Design token formats
TOKEN_FORMATS = ["css", "tailwind", "json", "scss"]
