"""Tests for the Gemini client wrapper."""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from gemini_visual_mcp.config import API_TIMEOUT_MS
from gemini_visual_mcp.gemini_client import (
    GeminiAuthError,
    GeminiClient,
    GeminiClientError,
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
            kwargs = mock_genai.Client.call_args.kwargs
            assert kwargs["api_key"] == "test-key-123"

    def test_client_configures_timeout_and_retry(self):
        """A hung connection used to block a worker thread forever."""
        with patch("gemini_visual_mcp.gemini_client.genai") as mock_genai:
            GeminiClient(api_key="k")
            http_options = mock_genai.Client.call_args.kwargs["http_options"]
            assert http_options.timeout == API_TIMEOUT_MS
            codes = http_options.retry_options.http_status_codes
            assert 429 in codes and 503 in codes
            # Permanent failures must never be retried.
            assert 400 not in codes and 404 not in codes


class TestErrorClassification:
    """Errors are classified from typed SDK exceptions, not substring matches."""

    def _client(self):
        with patch("gemini_visual_mcp.gemini_client.genai"):
            return GeminiClient(api_key="test-key")

    def _client_error(self, code, message="boom", details=None):
        err = genai_errors.ClientError.__new__(genai_errors.ClientError)
        Exception.__init__(err, message)
        err.code = code
        err.message = message
        err.details = details or {}
        err.status = None
        return err

    def test_auth_error_not_retried(self):
        client = self._client()
        func = MagicMock(side_effect=self._client_error(401, "invalid key"))
        with pytest.raises(GeminiAuthError):
            client._sync_call(func)
        assert func.call_count == 1

    def test_content_policy_from_details(self):
        client = self._client()
        func = MagicMock(side_effect=self._client_error(400, "blocked", {"reason": "SAFETY"}))
        with pytest.raises(GeminiContentPolicyError):
            client._sync_call(func)
        assert func.call_count == 1

    def test_quota_error(self):
        client = self._client()
        func = MagicMock(side_effect=self._client_error(429, "rate limited"))
        with pytest.raises(GeminiQuotaError):
            client._sync_call(func)

    def test_bad_model_id_fails_immediately(self):
        """A retired model id used to cost 3 calls and ~7s of sleeps."""
        client = self._client()
        func = MagicMock(side_effect=self._client_error(404, "model not found"))
        with pytest.raises(GeminiClientError) as excinfo:
            client._sync_call(func)
        assert func.call_count == 1
        assert not isinstance(excinfo.value, GeminiQuotaError)

    def test_byte_count_in_message_is_not_an_auth_error(self):
        """Substring matching used to read '401 bytes' as a 401 status."""
        client = self._client()
        func = MagicMock(side_effect=ValueError("response was 401 bytes"))
        with pytest.raises(GeminiClientError) as excinfo:
            client._sync_call(func)
        assert not isinstance(excinfo.value, GeminiAuthError)

    def test_server_error_is_wrapped(self):
        client = self._client()
        err = genai_errors.ServerError.__new__(genai_errors.ServerError)
        Exception.__init__(err, "503 unavailable")
        err.code = 503
        err.message = "unavailable"
        err.details = {}
        err.status = None
        func = MagicMock(side_effect=err)
        with pytest.raises(GeminiClientError):
            client._sync_call(func)


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
