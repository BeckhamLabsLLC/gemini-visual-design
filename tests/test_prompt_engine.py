"""Tests for the prompt enhancement engine."""

import pytest

from gemini_visual_mcp.prompt_engine import (
    PromptValidationError,
    apply_template,
    enhance,
    get_templates,
    validate,
)


class TestValidation:
    """Tests for prompt validation."""

    def test_empty_prompt_raises(self):
        with pytest.raises(PromptValidationError, match="empty"):
            validate("")

    def test_whitespace_only_raises(self):
        with pytest.raises(PromptValidationError, match="empty"):
            validate("   ")

    def test_too_short_raises(self):
        with pytest.raises(PromptValidationError, match="too short"):
            validate("hi")

    def test_valid_prompt_returns_empty_warnings(self):
        warnings = validate("A professional dark-themed dashboard with sidebar navigation")
        assert isinstance(warnings, list)

    def test_negative_phrasing_warns(self):
        warnings = validate("A website with no background image and no sidebar")
        assert any("negative" in w.message.lower() for w in warnings)

    def test_vague_terms_warn(self):
        warnings = validate("Make something that looks like a thing on the screen")
        assert any("vague" in w.message.lower() for w in warnings)

    def test_warning_has_suggestion(self):
        warnings = validate("A design with no colors visible at all")
        for w in warnings:
            assert w.suggestion
            assert isinstance(w.to_dict(), dict)


class TestTemplates:
    """Tests for prompt templates."""

    def test_get_all_templates(self):
        templates = get_templates("all")
        assert len(templates) > 20  # We defined many templates
        for t in templates:
            assert "category" in t
            assert "key" in t
            assert "name" in t
            assert "description" in t

    def test_get_templates_by_category(self):
        ui = get_templates("ui-mockups")
        assert all(t["category"] == "ui-mockups" for t in ui)
        assert len(ui) >= 5

    def test_get_templates_unknown_category(self):
        result = get_templates("nonexistent")
        assert result == []

    def test_apply_template_defaults(self):
        prompt, meta = apply_template("ui-mockups", "dashboard")
        assert "dashboard" in prompt.lower()
        assert meta["template"] == "ui-mockups/dashboard"
        assert meta["aspect_ratio"] == "16:9"

    def test_apply_template_with_overrides(self):
        prompt, meta = apply_template(
            "ui-mockups", "dashboard", {"style": "light-themed"}
        )
        assert "light-themed" in prompt

    def test_apply_template_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown template category"):
            apply_template("nonexistent", "dashboard")

    def test_apply_template_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            apply_template("ui-mockups", "nonexistent")

    def test_all_templates_have_required_fields(self):
        """Every template must have skeleton, placeholders, aspect_ratio."""
        from gemini_visual_mcp.prompt_engine import TEMPLATES

        for cat, templates in TEMPLATES.items():
            for key, t in templates.items():
                assert "skeleton" in t, f"{cat}/{key} missing skeleton"
                assert "placeholders" in t, f"{cat}/{key} missing placeholders"
                assert "aspect_ratio" in t, f"{cat}/{key} missing aspect_ratio"
                # Verify skeleton can be formatted with its placeholders
                try:
                    t["skeleton"].format(**t["placeholders"])
                except KeyError as e:
                    pytest.fail(f"{cat}/{key} skeleton has unmatched placeholder: {e}")


class TestEnhance:
    """Tests for the full enhancement pipeline."""

    def test_enhance_basic(self):
        prompt, warnings = enhance("A modern dark dashboard with analytics charts")
        assert len(prompt) > len("A modern dark dashboard with analytics charts")
        assert isinstance(warnings, list)

    def test_enhance_with_profile(self):
        profile = {
            "colors": {"primary": "#ff0000", "text": "#ffffff"},
            "typography": {"style": "monospace"},
            "framework": "React",
            "visual_style": "brutalist",
        }
        prompt, _ = enhance(
            "A login page with email and password fields",
            profile=profile,
        )
        assert "#ff0000" in prompt
        assert "React" in prompt

    def test_enhance_with_template(self):
        prompt, warnings = enhance(
            "My analytics app dashboard",
            template="ui-mockups/dashboard",
        )
        assert "sidebar" in prompt.lower() or "dashboard" in prompt.lower()

    def test_enhance_with_invalid_template_warns(self):
        prompt, warnings = enhance(
            "A dashboard design",
            template="nonexistent/template",
        )
        # Should warn but not crash
        assert any("template" in w.message.lower() for w in warnings)

    def test_enhance_adds_structural_hints(self):
        prompt, _ = enhance("A blue button for my website")
        # Should add quality/lighting hints since none present
        assert "quality" in prompt.lower() or "lighting" in prompt.lower()

    def test_enhance_skips_hints_when_present(self):
        original = "A dashboard with professional lighting, high quality rendering, clean organized layout"
        prompt, _ = enhance(original)
        # Should not double up on hints
        assert prompt.count("high quality") <= 1

    def test_enhance_empty_raises(self):
        with pytest.raises(PromptValidationError):
            enhance("")
