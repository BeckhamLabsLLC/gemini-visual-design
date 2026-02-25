"""Tests for image editing module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gemini_visual_mcp.image_edit import edit_image


class TestEditImage:
    """Tests for edit_image function."""

    @pytest.mark.asyncio
    async def test_basic_edit_returns_dict(self, tmp_path):
        img = tmp_path / "original.png"
        img.write_bytes(b"fake-png-data")

        mock_client = MagicMock()
        mock_client.edit_image_gemini = AsyncMock(
            return_value=[{"data": b"edited-data", "mime_type": "image/png", "text": None}]
        )

        with patch("gemini_visual_mcp.image_edit.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_edit.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "edit_result.png"
                result = await edit_image(
                    client=mock_client,
                    image_path=str(img),
                    instruction="Change the button color to blue",
                    cwd=str(tmp_path),
                )

        assert "path" in result
        assert result["original_path"] == str(img)
        assert result["instruction"] == "Change the button color to blue"
        assert result["model"] == "gemini-2.5-flash-image"

    @pytest.mark.asyncio
    async def test_style_profile_injection_when_preserve_style(self, tmp_path):
        img = tmp_path / "original.png"
        img.write_bytes(b"fake-png-data")

        mock_client = MagicMock()
        mock_client.edit_image_gemini = AsyncMock(
            return_value=[{"data": b"edited", "mime_type": "image/png"}]
        )

        mock_profile = {"colors": {"primary": "#ff0000"}, "visual_style": "dark mode"}

        with patch("gemini_visual_mcp.image_edit.load_profile", return_value=mock_profile):
            with patch("gemini_visual_mcp.image_edit.apply_to_prompt", return_value="enhanced instruction") as mock_apply:
                with patch("gemini_visual_mcp.image_edit.save_generated") as mock_save:
                    mock_save.return_value = tmp_path / "edit_result.png"
                    result = await edit_image(
                        client=mock_client,
                        image_path=str(img),
                        instruction="Make it brighter",
                        cwd=str(tmp_path),
                        preserve_style=True,
                    )

        mock_apply.assert_called_once_with(mock_profile, "Make it brighter")
        assert result["enhanced_instruction"] == "enhanced instruction"

    @pytest.mark.asyncio
    async def test_no_profile_injection_when_preserve_style_false(self, tmp_path):
        img = tmp_path / "original.png"
        img.write_bytes(b"fake-png-data")

        mock_client = MagicMock()
        mock_client.edit_image_gemini = AsyncMock(
            return_value=[{"data": b"edited", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_edit.load_profile") as mock_load:
            with patch("gemini_visual_mcp.image_edit.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "edit_result.png"
                result = await edit_image(
                    client=mock_client,
                    image_path=str(img),
                    instruction="Add shadow",
                    cwd=str(tmp_path),
                    preserve_style=False,
                )

        mock_load.assert_not_called()
        assert result["enhanced_instruction"] == "Add shadow"

    @pytest.mark.asyncio
    async def test_missing_image_raises(self):
        mock_client = MagicMock()

        with pytest.raises(FileNotFoundError):
            await edit_image(
                client=mock_client,
                image_path="/nonexistent/image.png",
                instruction="Edit this",
            )
