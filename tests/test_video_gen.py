"""Tests for video generation module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gemini_visual_mcp.video_gen import generate_video


class TestGenerateVideo:
    """Tests for generate_video function."""

    @pytest.mark.asyncio
    async def test_text_to_video(self, tmp_path):
        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_client.generate_video = AsyncMock(return_value=mock_operation)
        mock_client.poll_video_operation = AsyncMock(
            return_value=[{"data": b"video-bytes", "mime_type": "video/mp4"}]
        )

        with patch("gemini_visual_mcp.video_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.video_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "video_result.mp4"
                result = await generate_video(
                    client=mock_client,
                    prompt="A slow camera pan across a mountain landscape at sunrise",
                    model="veo-3.1-fast",
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        mock_client.generate_video.assert_called_once()
        mock_client.poll_video_operation.assert_called_once_with(mock_operation)
        assert "path" in result
        assert result["model"] == "veo-3.1-fast"
        assert "enhanced_prompt" in result
        assert "warnings" in result

    @pytest.mark.asyncio
    async def test_reference_image_read_and_passed(self, tmp_path):
        ref_img = tmp_path / "reference.png"
        ref_img.write_bytes(b"ref-image-data")

        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_client.generate_video = AsyncMock(return_value=mock_operation)
        mock_client.poll_video_operation = AsyncMock(
            return_value=[{"data": b"video-bytes", "mime_type": "video/mp4"}]
        )

        with patch("gemini_visual_mcp.video_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.video_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "video_result.mp4"
                await generate_video(
                    client=mock_client,
                    prompt="Animate this scene with gentle motion",
                    model="veo-3.1-fast",
                    reference_image=str(ref_img),
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        # Verify image data was passed to generate_video
        call_kwargs = mock_client.generate_video.call_args.kwargs
        assert call_kwargs["image_data"] == b"ref-image-data"
        assert call_kwargs["image_mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_missing_reference_image_raises(self, tmp_path):
        mock_client = MagicMock()

        with patch("gemini_visual_mcp.video_gen.load_profile", return_value=None):
            with pytest.raises(FileNotFoundError):
                await generate_video(
                    client=mock_client,
                    prompt="Animate this scene",
                    reference_image="/nonexistent/image.png",
                    cwd=str(tmp_path),
                    use_profile=False,
                )

    @pytest.mark.asyncio
    async def test_return_dict_structure(self, tmp_path):
        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_client.generate_video = AsyncMock(return_value=mock_operation)
        mock_client.poll_video_operation = AsyncMock(
            return_value=[{"data": b"video", "mime_type": "video/mp4"}]
        )

        with patch("gemini_visual_mcp.video_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.video_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "video.mp4"
                result = await generate_video(
                    client=mock_client,
                    prompt="A timelapse of clouds moving over a cityscape with dramatic lighting",
                    model="veo-3.1",
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        assert "path" in result
        assert "enhanced_prompt" in result
        assert "model" in result
        assert "warnings" in result
        assert result["model"] == "veo-3.1"

    @pytest.mark.asyncio
    async def test_no_results_raises_runtime_error(self, tmp_path):
        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_client.generate_video = AsyncMock(return_value=mock_operation)
        mock_client.poll_video_operation = AsyncMock(return_value=[])

        with patch("gemini_visual_mcp.video_gen.load_profile", return_value=None):
            with pytest.raises(RuntimeError, match="no results"):
                await generate_video(
                    client=mock_client,
                    prompt="A timelapse of clouds moving over a cityscape with dramatic lighting",
                    cwd=str(tmp_path),
                    use_profile=False,
                )
