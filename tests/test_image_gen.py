"""Tests for image generation module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gemini_visual_mcp.image_gen import auto_generate


class TestAutoGenerate:
    """Tests for automatic model selection."""

    @pytest.mark.asyncio
    async def test_auto_selects_gemini_by_default(self):
        mock_client = MagicMock()
        mock_client.generate_image_gemini = AsyncMock(
            return_value=[{"data": b"fake-image", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = "/tmp/gen_test.png"
                results = await auto_generate(
                    client=mock_client,
                    prompt="A simple blue button on a white background",
                    model="auto",
                    cwd="/tmp",
                    use_profile=False,
                )

        mock_client.generate_image_gemini.assert_called_once()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_auto_selects_imagen_for_final(self):
        mock_client = MagicMock()
        mock_client.generate_image_imagen = AsyncMock(
            return_value=[{"data": b"fake-image", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = "/tmp/gen_test.png"
                await auto_generate(
                    client=mock_client,
                    prompt="Final production hero image for the landing page",
                    model="auto",
                    cwd="/tmp",
                    use_profile=False,
                )

        mock_client.generate_image_imagen.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_gemini_model(self):
        mock_client = MagicMock()
        mock_client.generate_image_gemini = AsyncMock(
            return_value=[{"data": b"img", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = "/tmp/gen_test.png"
                await auto_generate(
                    client=mock_client,
                    prompt="A dashboard mockup design with modern styling",
                    model="gemini",
                    cwd="/tmp",
                    use_profile=False,
                )

        mock_client.generate_image_gemini.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_imagen_model(self):
        mock_client = MagicMock()
        mock_client.generate_image_imagen = AsyncMock(
            return_value=[{"data": b"img", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = "/tmp/gen_test.png"
                await auto_generate(
                    client=mock_client,
                    prompt="A dashboard mockup design with modern styling",
                    model="imagen",
                    count=2,
                    cwd="/tmp",
                    use_profile=False,
                )

        mock_client.generate_image_imagen.assert_called_once()
