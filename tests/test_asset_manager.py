"""Tests for asset manager module."""

import json
import time

import pytest

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
