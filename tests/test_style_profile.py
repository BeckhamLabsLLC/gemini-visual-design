"""Tests for style profile management."""

import json

from gemini_visual_mcp.config import STYLE_PROFILE_FILENAME
from gemini_visual_mcp.style_profile import (
    apply_to_prompt,
    auto_detect_profile,
    create_profile,
    find_profile,
    load_profile,
    update_profile,
)


class TestFindProfile:
    """Tests for profile discovery."""

    def test_find_in_current_dir(self, tmp_path):
        profile_path = tmp_path / STYLE_PROFILE_FILENAME
        profile_path.write_text('{"project_type": "web-app"}')
        found = find_profile(str(tmp_path))
        assert found == profile_path

    def test_find_in_parent_dir(self, tmp_path):
        profile_path = tmp_path / STYLE_PROFILE_FILENAME
        profile_path.write_text('{"project_type": "web-app"}')
        child = tmp_path / "src" / "components"
        child.mkdir(parents=True)
        found = find_profile(str(child))
        assert found == profile_path

    def test_not_found(self, tmp_path):
        found = find_profile(str(tmp_path))
        assert found is None


class TestCreateProfile:
    """Tests for profile creation."""

    def test_create_default(self, tmp_path):
        path = create_profile(str(tmp_path))
        assert path.is_file()
        with open(path) as f:
            profile = json.load(f)
        assert profile["project_type"] == "web-app"
        assert "colors" in profile
        assert "typography" in profile

    def test_create_with_overrides(self, tmp_path):
        path = create_profile(
            str(tmp_path),
            project_type="game",
            colors={"primary": "#ff0000"},
            visual_style="pixel art, retro",
        )
        with open(path) as f:
            profile = json.load(f)
        assert profile["project_type"] == "game"
        assert profile["colors"]["primary"] == "#ff0000"
        assert "pixel art" in profile["visual_style"]

    def test_create_preserves_default_colors(self, tmp_path):
        path = create_profile(
            str(tmp_path),
            colors={"primary": "#ff0000"},
        )
        with open(path) as f:
            profile = json.load(f)
        # Should merge, not replace
        assert profile["colors"]["primary"] == "#ff0000"
        assert "secondary" in profile["colors"]


class TestLoadProfile:
    """Tests for profile loading."""

    def test_load_valid(self, tmp_path):
        create_profile(str(tmp_path), project_type="landing-page")
        profile = load_profile(str(tmp_path))
        assert profile is not None
        assert profile["project_type"] == "landing-page"

    def test_load_missing(self, tmp_path):
        profile = load_profile(str(tmp_path))
        assert profile is None

    def test_load_invalid_json(self, tmp_path):
        (tmp_path / STYLE_PROFILE_FILENAME).write_text("not json")
        profile = load_profile(str(tmp_path))
        assert profile is None


class TestUpdateProfile:
    """Tests for profile updates."""

    def test_update_top_level(self, tmp_path):
        create_profile(str(tmp_path))
        update_profile(str(tmp_path), {"visual_style": "brutalist"})
        profile = load_profile(str(tmp_path))
        assert profile["visual_style"] == "brutalist"

    def test_update_nested_merge(self, tmp_path):
        create_profile(str(tmp_path))
        update_profile(str(tmp_path), {"colors": {"primary": "#000000"}})
        profile = load_profile(str(tmp_path))
        assert profile["colors"]["primary"] == "#000000"
        # Other colors should be preserved
        assert "secondary" in profile["colors"]

    def test_update_missing_profile(self, tmp_path):
        result = update_profile(str(tmp_path), {"visual_style": "new"})
        assert result is None


class TestApplyToPrompt:
    """Tests for profile application to prompts."""

    def test_apply_colors(self):
        profile = {
            "colors": {"primary": "#ff0000", "background": "#000000"},
            "typography": {},
        }
        result = apply_to_prompt(profile, "A dashboard")
        assert "#ff0000" in result
        assert "#000000" in result

    def test_apply_framework(self):
        profile = {"framework": "React + Tailwind CSS", "colors": {}, "typography": {}}
        result = apply_to_prompt(profile, "A button component")
        assert "React" in result

    def test_apply_design_system(self):
        profile = {"design_system": "Material Design 3", "colors": {}, "typography": {}}
        result = apply_to_prompt(profile, "A form layout")
        assert "Material Design 3" in result

    def test_apply_empty_profile(self):
        profile = {"colors": {}, "typography": {}}
        prompt = "A simple design"
        result = apply_to_prompt(profile, prompt)
        assert prompt in result

    def test_icon_style_applied_for_icon_prompts(self):
        profile = {
            "icon_style": "outlined, 24px, 2px stroke",
            "colors": {},
            "typography": {},
        }
        result = apply_to_prompt(profile, "Create an icon for settings")
        assert "outlined" in result


class TestAutoDetect:
    """Tests for auto-detection from project files."""

    def test_detect_from_package_json(self, tmp_path):
        pkg = {
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
            },
            "devDependencies": {
                "tailwindcss": "^3.0.0",
            },
        }
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        detected = auto_detect_profile(str(tmp_path))
        assert "React" in detected["framework"]
        assert "Tailwind" in detected["framework"]

    def test_detect_material_ui(self, tmp_path):
        pkg = {"dependencies": {"@mui/material": "^5.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        detected = auto_detect_profile(str(tmp_path))
        assert "Material UI" in detected["design_system"]

    def test_detect_css_variables(self, tmp_path):
        css = """:root {
  --color-primary: #3b82f6;
  --color-secondary: #8b5cf6;
  --text-color: #f8fafc;
}"""
        (tmp_path / "styles.css").write_text(css)
        detected = auto_detect_profile(str(tmp_path))
        assert detected["colors"]["primary"] == "#3b82f6"

    def test_detect_empty_project(self, tmp_path):
        detected = auto_detect_profile(str(tmp_path))
        assert detected["project_type"] == "web-app"  # default
