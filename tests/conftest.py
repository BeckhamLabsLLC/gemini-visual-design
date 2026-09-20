"""Shared fixtures.

The most important thing here is clean_env: without it the suite runs
against the developer's real GEMINI_API_KEY and CLAUDE_PROJECT_DIR, so a
test that accidentally builds a real client passes locally and fails in CI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gemini_visual_mcp import asset_manager, config

ENV_VARS = (
    "GEMINI_API_KEY",
    "CLAUDE_PROJECT_DIR",
    "GEMINI_VISUAL_PROJECT_DIR",
    "PROJECT_DIR",
    "GEMINI_VISUAL_VIDEO_TIMEOUT",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Keep the developer's real environment out of every test."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """A throwaway project directory that the server will resolve to."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def preview_dir(tmp_path, monkeypatch):
    """Redirect the preview cache into tmp_path."""
    target = tmp_path / "preview"
    target.mkdir()
    monkeypatch.setattr(asset_manager, "PREVIEW_DIR", target)
    return target


def make_image_part(data=b"\x89PNG_fake", mime_type="image/png"):
    part = MagicMock()
    part.inline_data.data = data
    part.inline_data.mime_type = mime_type
    part.text = None
    return part


def make_text_part(text):
    part = MagicMock()
    part.inline_data = None
    part.text = text
    return part


def make_response(parts=None, finish_reason=None, model_version=None):
    """Build a generate_content-shaped response mock."""
    candidate = MagicMock()
    candidate.finish_reason = finish_reason
    candidate.content.parts = parts if parts is not None else [make_image_part()]
    response = MagicMock()
    response.candidates = [candidate]
    response.prompt_feedback = None
    response.model_version = model_version
    return response


@pytest.fixture
def image_response():
    return make_response


@pytest.fixture
def fake_genai():
    """Patch the SDK module and hand back the mocked models surface."""
    with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
        models = mock_genai.Client.return_value.models
        models.generate_content.return_value = make_response()
        yield mock_genai


@pytest.fixture
def mock_client():
    """A GeminiClient stand-in with async methods pre-wired."""
    client = MagicMock()
    client.generate_image_gemini = AsyncMock(
        return_value=[
            {
                "data": b"fake",
                "mime_type": "image/png",
                "model": config.IMAGE_MODELS["fast"],
            }
        ]
    )
    client.edit_image_gemini = AsyncMock(
        return_value=[
            {
                "data": b"fake",
                "mime_type": "image/png",
                "model": config.IMAGE_MODELS["fast"],
            }
        ]
    )
    client.analyze_image = AsyncMock(return_value="{}")
    client.generate_text = AsyncMock(return_value="")
    client.generate_video = AsyncMock()
    client.poll_video_operation = AsyncMock(
        return_value=[{"data": b"fakevideo", "mime_type": "video/mp4"}]
    )
    return client


@pytest.fixture
def server():
    """A server with the SDK stubbed out and a pre-set client."""
    from gemini_visual_mcp.server import GeminiVisualDesignServer

    with patch("gemini_visual_mcp.server.Server"):
        with patch("gemini_visual_mcp.gemini_client.genai"):
            instance = GeminiVisualDesignServer()
            instance._client = MagicMock()
            return instance
