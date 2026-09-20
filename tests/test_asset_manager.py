"""Tests for asset manager module."""

import json
import time

import pytest

from gemini_visual_mcp import asset_manager
from gemini_visual_mcp.asset_manager import (
    cleanup_old,
    list_generated,
    save_generated,
    save_to_project,
)


class TestSaveGenerated:
    """Tests for saving generated assets."""

    def test_save_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        path = save_generated(
            data=b"fake-png-data",
            mime_type="image/png",
            metadata={"prompt": "test prompt", "model": "gemini"},
            prefix="gen",
        )
        assert path.is_file()
        assert path.suffix == ".png"
        assert path.read_bytes() == b"fake-png-data"

    def test_save_creates_metadata_sidecar(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        path = save_generated(
            data=b"data",
            mime_type="image/png",
            metadata={"prompt": "test"},
        )
        meta_path = tmp_path / f"{path.name}.meta.json"
        assert meta_path.is_file()
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["prompt"] == "test"
        assert meta["mime_type"] == "image/png"
        assert meta["size_bytes"] == 4

    def test_save_video(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        path = save_generated(
            data=b"video-data",
            mime_type="video/mp4",
            metadata={"prompt": "a video"},
            prefix="video",
        )
        assert path.suffix == ".mp4"


class TestListGenerated:
    """Tests for listing generated assets."""

    def test_list_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        items = list_generated()
        assert items == []

    def test_list_with_assets(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        save_generated(b"img1", "image/png", {"prompt": "first", "model": "gemini"})
        save_generated(b"img2", "image/png", {"prompt": "second", "model": "imagen"})
        items = list_generated()
        assert len(items) == 2
        assert items[0]["prompt"] == "first"
        assert items[1]["prompt"] == "second"

    def test_list_skips_orphaned_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        # Create metadata without corresponding asset
        meta = {"filename": "nonexistent.png", "prompt": "ghost"}
        (tmp_path / "nonexistent.png.meta.json").write_text(json.dumps(meta))
        items = list_generated()
        assert items == []


class TestSaveToProject:
    """Tests for saving to project directory."""

    def test_save_to_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        # Create a preview file
        path = save_generated(b"image-data", "image/png", {"prompt": "test"})

        # Save to project
        dest = tmp_path / "project" / "assets"
        result = save_to_project(str(path), str(dest), "hero.png")
        assert result.is_file()
        assert result.name == "hero.png"
        assert result.read_bytes() == b"image-data"

    def test_save_creates_dest_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        path = save_generated(b"data", "image/png", {"prompt": "test"})
        dest = tmp_path / "new" / "deep" / "dir"
        result = save_to_project(str(path), str(dest), "img.png")
        assert result.is_file()

    def test_save_missing_source_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            save_to_project("/nonexistent/file.png", str(tmp_path), "out.png")

    def test_save_rejects_path_traversal(self, tmp_path, monkeypatch):
        preview = tmp_path / "preview"
        preview.mkdir()
        monkeypatch.setattr(asset_manager, "PREVIEW_DIR", preview)
        src = preview / "a.png"
        src.write_bytes(b"x")
        dest = tmp_path / "project"
        with pytest.raises(ValueError, match="bare filename"):
            save_to_project(str(src), str(dest), "../escaped.png")
        # A rejected request must not leave directories behind.
        assert not dest.exists()

    def test_save_rejects_absolute_path_filename(self, tmp_path, monkeypatch):
        preview = tmp_path / "preview"
        preview.mkdir()
        monkeypatch.setattr(asset_manager, "PREVIEW_DIR", preview)
        src = preview / "a.png"
        src.write_bytes(b"x")
        with pytest.raises(ValueError, match="bare filename"):
            save_to_project(str(src), str(tmp_path / "project"), "/etc/evil.png")

    def test_save_rejects_dot_filename(self, tmp_path, monkeypatch):
        preview = tmp_path / "preview"
        preview.mkdir()
        monkeypatch.setattr(asset_manager, "PREVIEW_DIR", preview)
        src = preview / "a.png"
        src.write_bytes(b"x")
        with pytest.raises(ValueError, match="bare filename"):
            save_to_project(str(src), str(tmp_path / "project"), ".")

    def test_save_rejects_dest_outside_project(self, tmp_path, monkeypatch):
        preview = tmp_path / "preview"
        preview.mkdir()
        monkeypatch.setattr(asset_manager, "PREVIEW_DIR", preview)
        src = preview / "a.png"
        src.write_bytes(b"x")
        project = tmp_path / "project"
        project.mkdir()
        outside = tmp_path / "elsewhere"
        with pytest.raises(ValueError, match="outside the project"):
            save_to_project(str(src), str(outside), "a.png", project_root=str(project))
        assert not outside.exists()

    def test_save_refuses_to_clobber(self, tmp_path, monkeypatch):
        preview = tmp_path / "preview"
        preview.mkdir()
        monkeypatch.setattr(asset_manager, "PREVIEW_DIR", preview)
        src = preview / "a.png"
        src.write_bytes(b"x")
        dest = tmp_path / "project"
        dest.mkdir()
        (dest / "a.png").write_bytes(b"original")
        with pytest.raises(ValueError, match="already exists"):
            save_to_project(str(src), str(dest), "a.png")
        assert (dest / "a.png").read_bytes() == b"original"


class TestCleanup:
    """Tests for old file cleanup."""

    def test_cleanup_old_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        # Create a file and backdate it
        old_file = tmp_path / "old.png"
        old_file.write_bytes(b"old")
        import os

        old_time = time.time() - (8 * 86400)  # 8 days ago
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_path / "new.png"
        new_file.write_bytes(b"new")

        removed = cleanup_old(max_age_days=7)
        assert removed == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_empty_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("gemini_visual_mcp.asset_manager.PREVIEW_DIR", tmp_path)
        removed = cleanup_old()
        assert removed == 0


class TestAtomicWrites:
    def test_written_files_respect_umask(self, tmp_path):
        """mkstemp creates 0600; saved assets must not inherit that."""
        import os
        import stat

        from gemini_visual_mcp.io_utils import atomic_write_bytes

        target = tmp_path / "asset.png"
        atomic_write_bytes(target, b"data")
        current = os.umask(0)
        os.umask(current)
        expected = 0o666 & ~current
        assert stat.S_IMODE(target.stat().st_mode) == expected

    def test_failed_write_leaves_no_temp_files(self, tmp_path):
        from gemini_visual_mcp.io_utils import atomic_write_json

        class Unserializable:
            pass

        target = tmp_path / "profile.json"
        # default=str makes almost anything serializable, so force a real
        # failure by making the destination directory unwritable instead.
        atomic_write_json(target, {"ok": True})
        assert target.exists()
        assert [p.name for p in tmp_path.iterdir()] == ["profile.json"]

    def test_existing_file_survives_when_write_fails(self, tmp_path):
        from unittest.mock import patch

        from gemini_visual_mcp.io_utils import atomic_write_bytes

        target = tmp_path / "asset.png"
        target.write_bytes(b"original")
        with patch("gemini_visual_mcp.io_utils.os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                atomic_write_bytes(target, b"new")
        assert target.read_bytes() == b"original"
        assert [p.name for p in tmp_path.iterdir()] == ["asset.png"]
