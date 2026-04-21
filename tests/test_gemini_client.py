"""Tests for the Gemini client wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from gemini_visual_mcp.gemini_client import (
    GeminiAuthError,
    GeminiClient,
    GeminiContentPolicyError,
    GeminiQuotaError,
)


class TestGeminiClientInit:
    """Tests for client initialization."""

    def test_missing_api_key_raises(self):
        with patch("gemini_visual_mcp.gemini_client.GEMINI_API_KEY", ""):
            with pytest.raises(GeminiAuthError, match="GEMINI_API_KEY"):
                GeminiClient(api_key="")

    def test_explicit_api_key(self):
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            GeminiClient(api_key="test-key-123")
            mock_genai.Client.assert_called_once_with(api_key="test-key-123")


class TestRetryLogic:
    """Tests for retry and error handling."""

    def test_sync_call_auth_error_no_retry(self):
        with patch("gemini_visual_mcp.gemini_client.genai"):
            client = GeminiClient(api_key="test-key")
            func = MagicMock(side_effect=Exception("401 authentication failed"))
            with pytest.raises(GeminiAuthError):
                client._sync_call(func)
            # Should only be called once (no retry)
            assert func.call_count == 1

    def test_sync_call_content_policy_no_retry(self):
        with patch("gemini_visual_mcp.gemini_client.genai"):
            client = GeminiClient(api_key="test-key")
            func = MagicMock(side_effect=Exception("Content blocked by safety policy"))
            with pytest.raises(GeminiContentPolicyError):
                client._sync_call(func)
            assert func.call_count == 1

    def test_sync_call_quota_retries(self):
        with patch("gemini_visual_mcp.gemini_client.genai"):
            with patch("gemini_visual_mcp.gemini_client.time.sleep"):
                client = GeminiClient(api_key="test-key")
                func = MagicMock(side_effect=Exception("429 quota exceeded"))
                with pytest.raises(GeminiQuotaError):
                    client._sync_call(func)
                assert func.call_count == 3  # MAX_RETRIES

    def test_sync_call_success_after_retry(self):
        with patch("gemini_visual_mcp.gemini_client.genai"):
            with patch("gemini_visual_mcp.gemini_client.time.sleep"):
                client = GeminiClient(api_key="test-key")
                func = MagicMock(side_effect=[Exception("transient error"), "success"])
                result = client._sync_call(func)
                assert result == "success"
                assert func.call_count == 2


class TestGenerateImageWithReference:
    """Tests for reference image support in generate_image_gemini."""

    @pytest.mark.asyncio
    async def test_reference_image_sent_as_multipart_contents(self):
        """When reference image is provided, contents should be a list with Part + prompt."""
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            mock_models = MagicMock()
            mock_genai.Client.return_value.models = mock_models

            # Build a fake response with an image part
            mock_part = MagicMock()
            mock_part.inline_data = MagicMock()
            mock_part.inline_data.data = b"generated-image"
            mock_part.inline_data.mime_type = "image/png"
            mock_part.text = None

            mock_candidate = MagicMock()
            mock_candidate.content.parts = [mock_part]
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_models.generate_content = MagicMock(return_value=mock_response)

            client = GeminiClient(api_key="test-key")
            await client.generate_image_gemini(
                prompt="A warrior in matching style",
                reference_image_data=b"ref-image-bytes",
                reference_mime_type="image/png",
            )

            call_args = mock_models.generate_content.call_args
            contents = call_args.kwargs["contents"]
            # Should be a list with image Part and text prompt
            assert isinstance(contents, list)
            assert len(contents) == 2
            assert contents[1] == "A warrior in matching style"

    @pytest.mark.asyncio
    async def test_no_reference_sends_plain_string(self):
        """Without reference image, contents should be a plain string."""
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            mock_models = MagicMock()
            mock_genai.Client.return_value.models = mock_models

            mock_part = MagicMock()
            mock_part.inline_data = MagicMock()
            mock_part.inline_data.data = b"generated-image"
            mock_part.inline_data.mime_type = "image/png"
            mock_part.text = None

            mock_candidate = MagicMock()
            mock_candidate.content.parts = [mock_part]
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_models.generate_content = MagicMock(return_value=mock_response)

            client = GeminiClient(api_key="test-key")
            await client.generate_image_gemini(
                prompt="A simple landscape",
            )

            call_args = mock_models.generate_content.call_args
            contents = call_args.kwargs["contents"]
            assert isinstance(contents, str)
            assert contents == "A simple landscape"


class TestVideoModelMap:
    """Tests for video model name mapping."""

    def test_model_mapping(self):
        from gemini_visual_mcp.gemini_client import VIDEO_MODEL_MAP

        assert "veo-3.1" in VIDEO_MODEL_MAP
        assert "veo-3.1-fast" in VIDEO_MODEL_MAP
        # Retired model (removed from API on 2026-04-02) must not be listed.
        assert "veo-2" not in VIDEO_MODEL_MAP


class TestVideoGenerationWithImage:
    """Regression tests for image-to-video prompt handling.

    Veo accepts a prompt alongside an image input — the prompt guides how the
    reference frame should be animated. A previous bug silently dropped the
    prompt whenever an image was provided.
    """

    @pytest.mark.asyncio
    async def test_prompt_passed_with_image(self):
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            mock_models = MagicMock()
            mock_genai.Client.return_value.models = mock_models
            mock_models.generate_videos = MagicMock(return_value="op")

            client = GeminiClient(api_key="test-key")
            await client.generate_video(
                prompt="dolly forward through a misty forest",
                model="veo-3.1-fast",
                image_data=b"image-bytes",
                image_mime_type="image/png",
            )

            call_kwargs = mock_models.generate_videos.call_args.kwargs
            assert call_kwargs["prompt"] == "dolly forward through a misty forest"
            assert call_kwargs["image"] is not None

    @pytest.mark.asyncio
    async def test_prompt_passed_without_image(self):
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            mock_models = MagicMock()
            mock_genai.Client.return_value.models = mock_models
            mock_models.generate_videos = MagicMock(return_value="op")

            client = GeminiClient(api_key="test-key")
            await client.generate_video(
                prompt="a calm ocean at sunset",
                model="veo-3.1-fast",
            )

            call_kwargs = mock_models.generate_videos.call_args.kwargs
            assert call_kwargs["prompt"] == "a calm ocean at sunset"
            assert call_kwargs["image"] is None


class TestPollVideoOperation:
    """Regression tests for video operation polling.

    A previous bug called operation.reload() inside the poll loop, which does
    not exist on google-genai's GenerateVideosOperation pydantic model — every
    poll iteration would raise AttributeError after the first 5-second sleep.
    The correct SDK pattern is client.operations.get(operation), which returns
    a fresh operation object.
    """

    @pytest.mark.asyncio
    async def test_poll_uses_operations_get_not_reload(self):
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            mock_client_inst = mock_genai.Client.return_value

            op_pending = MagicMock(done=False)
            op_done = MagicMock(done=True)
            op_done.response.generated_videos = [MagicMock(video="video-ref")]
            mock_client_inst.operations.get.return_value = op_done
            mock_client_inst.files.download.return_value = b"video-bytes"

            with patch("gemini_visual_mcp.gemini_client.time.sleep"):
                client = GeminiClient(api_key="test-key")
                results = await client.poll_video_operation(op_pending)

            mock_client_inst.operations.get.assert_called_with(op_pending)
            assert results == [{"data": b"video-bytes", "mime_type": "video/mp4"}]

    @pytest.mark.asyncio
    async def test_poll_returns_immediately_when_done(self):
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            mock_client_inst = mock_genai.Client.return_value

            op_done = MagicMock(done=True)
            op_done.response.generated_videos = [MagicMock(video="video-ref")]
            mock_client_inst.files.download.return_value = b"video-bytes"

            client = GeminiClient(api_key="test-key")
            results = await client.poll_video_operation(op_done)

            # Operation already done — no polling required.
            mock_client_inst.operations.get.assert_not_called()
            assert results == [{"data": b"video-bytes", "mime_type": "video/mp4"}]
