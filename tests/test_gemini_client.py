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


class TestVideoModelMap:
    """Tests for video model name mapping."""

    def test_model_mapping(self):
        from gemini_visual_mcp.gemini_client import VIDEO_MODEL_MAP

        assert "veo-2" in VIDEO_MODEL_MAP
        assert "veo-3.1" in VIDEO_MODEL_MAP
        assert "veo-3.1-fast" in VIDEO_MODEL_MAP
