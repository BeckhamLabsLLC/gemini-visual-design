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
    async def test_auto_selects_pro_for_final(self, mock_client, tmp_path):
        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "gen_test.png"
                await auto_generate(
                    client=mock_client,
                    prompt="Final production hero image for the landing page",
                    model="auto",
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        assert mock_client.generate_image_gemini.call_args.kwargs["tier"] == "pro"

    @pytest.mark.asyncio
    async def test_auto_selects_fast_for_ordinary_prompt(self, mock_client, tmp_path):
        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "gen_test.png"
                await auto_generate(
                    client=mock_client,
                    prompt="A sidebar navigation component with icons",
                    model="auto",
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        assert mock_client.generate_image_gemini.call_args.kwargs["tier"] == "fast"

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
    async def test_explicit_legacy_imagen_maps_to_pro(self, mock_client, tmp_path):
        """Imagen 4 is retired; the old name must still work and warn."""
        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "gen_test.png"
                results = await auto_generate(
                    client=mock_client,
                    prompt="A dashboard mockup design with modern styling",
                    model="imagen",
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        assert mock_client.generate_image_gemini.call_args.kwargs["tier"] == "pro"
        warnings = results[0]["warnings"]
        assert any("legacy" in str(w).lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_count_fans_out_to_separate_calls(self, mock_client, tmp_path):
        """Image models reject candidate_count > 1, so count means N calls."""
        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = tmp_path / "gen_test.png"
                results = await auto_generate(
                    client=mock_client,
                    prompt="A dashboard mockup design with modern styling",
                    model="fast",
                    count=3,
                    cwd=str(tmp_path),
                    use_profile=False,
                )

        assert mock_client.generate_image_gemini.call_count == 3
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_reference_image_routes_to_gemini(self):
        """When reference_image is provided with model='auto', Gemini is used."""
        mock_client = MagicMock()
        mock_client.generate_image_gemini = AsyncMock(
            return_value=[{"data": b"img", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch(
                "gemini_visual_mcp.image_gen.read_image", return_value=(b"ref", "image/png")
            ):
                with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                    mock_save.return_value = "/tmp/gen_test.png"
                    await auto_generate(
                        client=mock_client,
                        prompt="A warrior character with sword and shield design",
                        model="auto",
                        cwd="/tmp",
                        use_profile=False,
                        reference_image="/tmp/ref.png",
                    )

        mock_client.generate_image_gemini.assert_called_once()
        # Verify reference image bytes were passed
        call_kwargs = mock_client.generate_image_gemini.call_args.kwargs
        assert call_kwargs["reference_image_data"] == b"ref"
        assert call_kwargs["reference_mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_reference_image_keeps_pro_tier(self, mock_client, tmp_path):
        """Every tier accepts a reference image now, so none is forced away."""
        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch(
                "gemini_visual_mcp.image_gen.read_image", return_value=(b"ref", "image/png")
            ):
                with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                    mock_save.return_value = tmp_path / "gen_test.png"
                    await auto_generate(
                        client=mock_client,
                        prompt="Final production character portrait design",
                        model="pro",
                        cwd=str(tmp_path),
                        use_profile=False,
                        reference_image=str(tmp_path / "ref.png"),
                    )

        kwargs = mock_client.generate_image_gemini.call_args.kwargs
        assert kwargs["tier"] == "pro"
        assert kwargs["reference_image_data"] == b"ref"

    @pytest.mark.asyncio
    async def test_reference_image_from_profile(self):
        """When profile has reference_image and none is explicitly passed, profile one is used."""
        mock_client = MagicMock()
        mock_client.generate_image_gemini = AsyncMock(
            return_value=[{"data": b"img", "mime_type": "image/png"}]
        )

        profile = {"reference_image": "/tmp/profile_ref.png", "colors": {}}

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=profile):
            with patch("gemini_visual_mcp.image_gen.Path") as mock_path:
                mock_path.return_value.is_file.return_value = True
                with patch(
                    "gemini_visual_mcp.image_gen.read_image", return_value=(b"ref", "image/png")
                ):
                    with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                        mock_save.return_value = "/tmp/gen_test.png"
                        await auto_generate(
                            client=mock_client,
                            prompt="A mage character with robes and staff design",
                            model="gemini",
                            cwd="/tmp",
                            use_profile=True,
                        )

        # Should have used the profile's reference image
        call_kwargs = mock_client.generate_image_gemini.call_args.kwargs
        assert call_kwargs["reference_image_data"] == b"ref"

    @pytest.mark.asyncio
    async def test_no_reference_image_unchanged(self):
        """Without reference_image, existing behavior is unchanged."""
        mock_client = MagicMock()
        mock_client.generate_image_gemini = AsyncMock(
            return_value=[{"data": b"img", "mime_type": "image/png"}]
        )

        with patch("gemini_visual_mcp.image_gen.load_profile", return_value=None):
            with patch("gemini_visual_mcp.image_gen.save_generated") as mock_save:
                mock_save.return_value = "/tmp/gen_test.png"
                await auto_generate(
                    client=mock_client,
                    prompt="A simple blue button on a white background design",
                    model="auto",
                    cwd="/tmp",
                    use_profile=False,
                )

        call_kwargs = mock_client.generate_image_gemini.call_args.kwargs
        assert call_kwargs["reference_image_data"] is None
        assert call_kwargs["reference_mime_type"] is None
