"""Project-root resolution.

The style profile is the plugin's headline feature and it depends entirely
on resolving the user's project directory correctly. Note that .mcp.json's
"cwd" key is ignored by Claude Code (anthropics/claude-code#17565), so the
env vars are the only reliable signal.
"""

import pytest

from gemini_visual_mcp.paths import PLUGIN_ROOT, ProjectRootError, resolve_project_root
from gemini_visual_mcp.style_profile import find_profile


class TestResolveProjectRoot:
    def test_claude_project_dir_is_used(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        root, source = resolve_project_root()
        assert root == tmp_path.resolve()
        assert source == "CLAUDE_PROJECT_DIR"

    def test_namespaced_override_wins(self, tmp_path, monkeypatch):
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.setenv("GEMINI_VISUAL_PROJECT_DIR", str(other))
        root, source = resolve_project_root()
        assert root == other.resolve()
        assert source == "GEMINI_VISUAL_PROJECT_DIR"

    def test_unnamespaced_project_dir_is_ignored(self, tmp_path, monkeypatch):
        """PROJECT_DIR collides with common build tooling; it must not win."""
        monkeypatch.setenv("PROJECT_DIR", str(tmp_path / "hijacked"))
        monkeypatch.chdir(tmp_path)
        root, source = resolve_project_root()
        assert root == tmp_path.resolve()
        assert source == "cwd"

    def test_nonexistent_env_dir_falls_through(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "does-not-exist"))
        monkeypatch.chdir(tmp_path)
        root, source = resolve_project_root()
        assert root == tmp_path.resolve()
        assert source == "cwd"

    def test_falls_back_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        root, source = resolve_project_root()
        assert root == tmp_path.resolve()
        assert source == "cwd"

    def test_strict_refuses_to_resolve_inside_the_plugin(self, monkeypatch):
        """Writing a profile into the plugin's own tree is never intended."""
        monkeypatch.chdir(PLUGIN_ROOT)
        with pytest.raises(ProjectRootError, match="inside the plugin"):
            resolve_project_root(strict=True)

    def test_lenient_inside_plugin_warns_but_proceeds(self, monkeypatch):
        """A read shouldn't fail a paid API call over path resolution."""
        monkeypatch.chdir(PLUGIN_ROOT)
        root, source = resolve_project_root(strict=False)
        assert root == PLUGIN_ROOT.resolve()
        assert source == "cwd"


class TestFindProfileBoundary:
    def test_finds_profile_in_project(self, tmp_path):
        (tmp_path / ".gemini-design-profile.json").write_text("{}")
        assert find_profile(str(tmp_path)) is not None

    def test_finds_profile_in_parent(self, tmp_path):
        (tmp_path / ".gemini-design-profile.json").write_text("{}")
        child = tmp_path / "src" / "components"
        child.mkdir(parents=True)
        assert find_profile(str(child)) == tmp_path / ".gemini-design-profile.json"

    def test_stops_at_the_git_boundary(self, tmp_path):
        """A stray profile above the repo must not leak into every project."""
        (tmp_path / ".gemini-design-profile.json").write_text("{}")
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        assert find_profile(str(repo)) is None
