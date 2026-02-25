"""Tests for design analysis module."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gemini_visual_mcp.analyzer import ANALYSIS_PROMPTS, analyze_design


class TestAnalyzeDesign:
    """Tests for analyze_design function."""

    @pytest.mark.asyncio
    async def test_returns_structured_dict(self, tmp_path):
        img = tmp_path / "design.png"
        img.write_bytes(b"fake-png")

        mock_client = MagicMock()
        analysis_json = json.dumps({
            "overall_score": 8,
            "categories": {"color": {"score": 9, "summary": "Good"}},
            "top_issues": [],
            "strengths": ["Clean layout"],
            "priority_improvements": [],
        })
        mock_client.analyze_image = AsyncMock(return_value=analysis_json)

        result = await analyze_design(
            client=mock_client,
            image_path=str(img),
            focus="overall",
            project_type="general",
        )

        assert result["image_path"] == str(img)
        assert result["focus"] == "overall"
        assert result["project_type"] == "general"
        assert result["overall_score"] == 8

    @pytest.mark.asyncio
    async def test_json_parsing_from_markdown_fences(self, tmp_path):
        img = tmp_path / "design.png"
        img.write_bytes(b"fake-png")

        mock_client = MagicMock()
        # Response wrapped in markdown code fences
        wrapped = '```json\n{"score": 7, "issues": []}\n```'
        mock_client.analyze_image = AsyncMock(return_value=wrapped)

        result = await analyze_design(
            client=mock_client,
            image_path=str(img),
            focus="color",
        )

        assert result["score"] == 7
        assert result["issues"] == []

    @pytest.mark.asyncio
    async def test_fallback_to_raw_analysis(self, tmp_path):
        img = tmp_path / "design.png"
        img.write_bytes(b"fake-png")

        mock_client = MagicMock()
        mock_client.analyze_image = AsyncMock(return_value="This is not valid JSON at all")

        result = await analyze_design(
            client=mock_client,
            image_path=str(img),
            focus="layout",
        )

        assert "raw_analysis" in result
        assert result["raw_analysis"] == "This is not valid JSON at all"
        assert "parse_error" in result

    @pytest.mark.asyncio
    async def test_invalid_focus_raises(self, tmp_path):
        img = tmp_path / "design.png"
        img.write_bytes(b"fake-png")

        mock_client = MagicMock()

        with pytest.raises(ValueError, match="Unknown focus"):
            await analyze_design(
                client=mock_client,
                image_path=str(img),
                focus="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_missing_image_raises(self):
        mock_client = MagicMock()

        with pytest.raises(FileNotFoundError):
            await analyze_design(
                client=mock_client,
                image_path="/nonexistent/image.png",
            )

    @pytest.mark.asyncio
    async def test_project_context_game(self, tmp_path):
        img = tmp_path / "game.png"
        img.write_bytes(b"fake")

        mock_client = MagicMock()
        mock_client.analyze_image = AsyncMock(return_value='{"score": 5}')

        await analyze_design(
            client=mock_client,
            image_path=str(img),
            focus="overall",
            project_type="game",
        )

        # Verify the game context was included in the prompt
        call_args = mock_client.analyze_image.call_args
        prompt = call_args.kwargs["analysis_prompt"]
        assert "game" in prompt.lower()

    @pytest.mark.asyncio
    async def test_project_context_landing_page(self, tmp_path):
        img = tmp_path / "lp.png"
        img.write_bytes(b"fake")

        mock_client = MagicMock()
        mock_client.analyze_image = AsyncMock(return_value='{"score": 5}')

        await analyze_design(
            client=mock_client,
            image_path=str(img),
            focus="overall",
            project_type="landing-page",
        )

        call_args = mock_client.analyze_image.call_args
        prompt = call_args.kwargs["analysis_prompt"]
        assert "landing page" in prompt.lower()

    @pytest.mark.asyncio
    async def test_project_context_web_app(self, tmp_path):
        img = tmp_path / "app.png"
        img.write_bytes(b"fake")

        mock_client = MagicMock()
        mock_client.analyze_image = AsyncMock(return_value='{"score": 5}')

        await analyze_design(
            client=mock_client,
            image_path=str(img),
            focus="overall",
            project_type="web-app",
        )

        call_args = mock_client.analyze_image.call_args
        prompt = call_args.kwargs["analysis_prompt"]
        assert "web application" in prompt.lower()


class TestAnalysisPrompts:
    """Tests for analysis prompt constants."""

    def test_all_focus_areas_have_prompts(self):
        expected = ["color", "layout", "typography", "overall"]
        for focus in expected:
            assert focus in ANALYSIS_PROMPTS

    def test_prompts_contain_json_structure(self):
        for focus, prompt in ANALYSIS_PROMPTS.items():
            assert "JSON" in prompt or "json" in prompt
            assert "{project_context}" in prompt
