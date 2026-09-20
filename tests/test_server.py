"""Tests for MCP server tool routing and error handling."""

from unittest.mock import AsyncMock, patch

import pytest


class TestToolRouting:
    """Tests for tool routing to correct handlers."""

    @pytest.mark.asyncio
    async def test_generate_image(self, server):
        with patch("gemini_visual_mcp.server.auto_generate") as mock_gen:
            mock_gen.return_value = [
                {
                    "path": "/tmp/gen.png",
                    "model": "gemini",
                    "enhanced_prompt": "enhanced",
                    "warnings": [],
                }
            ]
            with patch("gemini_visual_mcp.server.cleanup_old"):
                result = await server._handle_tool(
                    "generate_image", {"prompt": "A test image with blue background and white text"}
                )

        assert "generated" in result
        assert len(result["generated"]) == 1

    @pytest.mark.asyncio
    async def test_edit_image(self, server):
        with patch("gemini_visual_mcp.server.edit_image") as mock_edit:
            mock_edit.return_value = {
                "path": "/tmp/edit.png",
                "original_path": "/tmp/original.png",
                "instruction": "make blue",
                "model": "gemini-2.5-flash-image",
            }
            result = await server._handle_tool(
                "edit_image",
                {
                    "image_path": "/tmp/original.png",
                    "instruction": "make blue",
                },
            )

        assert result["edited_path"] == "/tmp/edit.png"
        assert result["original_path"] == "/tmp/original.png"

    @pytest.mark.asyncio
    async def test_analyze_design(self, server):
        with patch("gemini_visual_mcp.server.analyze_design") as mock_analyze:
            mock_analyze.return_value = {
                "overall_score": 8,
                "image_path": "/tmp/design.png",
                "focus": "overall",
                "project_type": "general",
            }
            result = await server._handle_tool(
                "analyze_design",
                {
                    "image_path": "/tmp/design.png",
                },
            )

        assert result["overall_score"] == 8

    @pytest.mark.asyncio
    async def test_generate_video(self, server):
        with patch("gemini_visual_mcp.server.generate_video") as mock_video:
            mock_video.return_value = {
                "path": "/tmp/video.mp4",
                "model": "veo-3.1-fast",
                "enhanced_prompt": "enhanced",
                "warnings": [],
            }
            result = await server._handle_tool(
                "generate_video",
                {
                    "prompt": "A sweeping aerial shot of mountains at golden hour",
                },
            )

        assert result["video_path"] == "/tmp/video.mp4"
        assert result["model"] == "veo-3.1-fast"

    @pytest.mark.asyncio
    async def test_save_asset(self, server, project_root):
        with patch("gemini_visual_mcp.server.save_to_project") as mock_save:
            mock_save.return_value = "/project/assets/hero.png"
            result = await server._handle_tool(
                "save_asset",
                {
                    "temp_path": "/tmp/gen.png",
                    "destination_dir": "assets",
                    "filename": "hero.png",
                },
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_generated(self, server):
        with patch("gemini_visual_mcp.server.list_generated") as mock_list:
            mock_list.return_value = [
                {"name": "gen_1.png", "prompt": "test"},
            ]
            result = await server._handle_tool("list_generated", {})

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_generate_design_tokens(self, server):
        server._client.generate_text = AsyncMock(return_value=":root { --primary: #3b82f6; }")

        with patch("gemini_visual_mcp.server.load_profile", return_value=None):
            result = await server._handle_tool(
                "generate_design_tokens",
                {
                    "description": "Modern dark theme design system",
                },
            )

        assert "tokens" in result
        assert result["format"] == "css"

    @pytest.mark.asyncio
    async def test_init_style_profile(self, server):
        with patch("gemini_visual_mcp.server.auto_detect_profile") as mock_detect:
            mock_detect.return_value = {"project_type": "web-app", "colors": {}, "typography": {}}
            with patch("gemini_visual_mcp.server.create_profile") as mock_create:
                mock_create.return_value = "/tmp/.gemini-design-profile.json"
                result = await server._handle_tool(
                    "init_style_profile",
                    {
                        "project_type": "web-app",
                    },
                )

        assert "profile_path" in result

    @pytest.mark.asyncio
    async def test_get_prompt_templates(self, server):
        result = await server._handle_tool("get_prompt_templates", {"category": "all"})
        assert "templates" in result
        assert result["count"] > 0

    @pytest.mark.asyncio
    async def test_generate_image_with_reference(self, server):
        with patch("gemini_visual_mcp.server.auto_generate") as mock_gen:
            mock_gen.return_value = [
                {
                    "path": "/tmp/gen.png",
                    "model": "gemini",
                    "enhanced_prompt": "enhanced",
                    "warnings": [],
                }
            ]
            with patch("gemini_visual_mcp.server.cleanup_old"):
                await server._handle_tool(
                    "generate_image",
                    {
                        "prompt": "A warrior character with armor and sword design",
                        "reference_image": "/tmp/ref_character.png",
                    },
                )

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args.kwargs
        assert call_kwargs["reference_image"] == "/tmp/ref_character.png"

    @pytest.mark.asyncio
    async def test_unknown_tool(self, server):
        """An unknown tool must not look like a successful call."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await server._handle_tool("nonexistent_tool", {})
