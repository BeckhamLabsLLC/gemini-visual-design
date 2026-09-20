"""Guards against the bug class that broke this plugin.

Google retired imagen-4.0-generate-001 on 2026-08-17 and the plugin kept
pinning it, so every "finalize" call 404'd after three retries. It also
pinned gemini-3.1-flash-image-preview past its announced 2026-06-25
shutdown. These tests make both mistakes impossible to reintroduce quietly.
"""

import ast
import re
from pathlib import Path

import pytest

from gemini_visual_mcp import config
from gemini_visual_mcp.gemini_client import VIDEO_MODEL_MAP

SRC = Path(__file__).resolve().parents[1] / "src" / "gemini_visual_mcp"

# Verified present via models.list() against the live API.
KNOWN_MODEL_IDS = frozenset(
    {
        "gemini-3.1-flash-image",
        "gemini-3.1-flash-lite-image",
        "gemini-3-pro-image",
        "gemini-2.5-flash",
        "veo-3.1-generate-preview",
        "veo-3.1-fast-generate-preview",
        "veo-3.1-lite-generate-preview",
    }
)


def _python_sources():
    return [p for p in SRC.glob("*.py")]


class TestConfiguredModelIds:
    @pytest.mark.parametrize("tier", ["draft", "fast", "pro"])
    def test_image_model_is_known(self, tier):
        assert config.IMAGE_MODELS[tier] in KNOWN_MODEL_IDS

    def test_text_model_is_known(self):
        assert config.GEMINI_FLASH_TEXT in KNOWN_MODEL_IDS

    def test_video_models_are_known(self):
        for model_id in VIDEO_MODEL_MAP.values():
            assert model_id in KNOWN_MODEL_IDS

    def test_no_imagen_model_string_in_source(self):
        """Imagen is retired. Prose may mention it; a model string may not."""
        offenders = []
        for path in _python_sources():
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if re.search(r"imagen-\d", node.value):
                        offenders.append(f"{path.name}:{node.lineno}")
        assert offenders == [], f"retired imagen model id in: {offenders}"

    def test_image_models_are_not_preview_builds(self):
        """Preview ids get retired on Google's schedule; GA ids don't."""
        for tier, model_id in config.IMAGE_MODELS.items():
            assert not model_id.endswith("-preview"), (
                f"tier {tier!r} pins a preview model ({model_id}); use the GA id"
            )

    def test_no_hardcoded_image_model_literals(self):
        """Model strings must come from config, or metadata starts lying."""
        pattern = re.compile(r'"gemini-[\d.]+-(?:flash|pro)[\w-]*image[\w-]*"')
        offenders = []
        for p in _python_sources():
            if p.name == "config.py":
                continue
            if pattern.search(p.read_text()):
                offenders.append(p.name)
        assert offenders == [], f"hardcoded image model id in: {offenders}"


class TestTierResolution:
    @pytest.mark.parametrize(
        "given,expected",
        [("imagen", "pro"), ("gemini", "fast"), ("flash", "fast"), ("lite", "draft")],
    )
    def test_legacy_names_still_resolve(self, given, expected):
        tier, warning = config.resolve_image_tier(given)
        assert tier == expected
        assert warning and "legacy" in warning.lower()

    @pytest.mark.parametrize("given", ["draft", "fast", "pro"])
    def test_current_names_resolve_without_warning(self, given):
        tier, warning = config.resolve_image_tier(given)
        assert tier == given
        assert warning is None

    def test_auto_passes_through(self):
        assert config.resolve_image_tier("auto") == ("auto", None)

    def test_garbage_falls_back_rather_than_raising(self):
        tier, warning = config.resolve_image_tier("nonsense-9000")
        assert tier == config.DEFAULT_IMAGE_TIER
        assert warning

    def test_legacy_names_are_not_advertised_in_the_enum(self):
        """The enum is the model's menu; retired names don't belong on it."""
        assert "imagen" not in config.MODEL_CHOICES_IMAGE
        assert "gemini" not in config.MODEL_CHOICES_IMAGE


class TestResolutionClamping:
    def test_4k_is_clamped_on_draft_tier(self):
        resolution, warning = config.clamp_resolution("draft", "4K")
        assert resolution == "1K"
        assert warning

    def test_supported_resolution_passes_through(self):
        assert config.clamp_resolution("pro", "4K") == ("4K", None)

    def test_unknown_resolution_falls_back(self):
        resolution, warning = config.clamp_resolution("fast", "8K")
        assert resolution == config.DEFAULT_RESOLUTION
        assert warning
