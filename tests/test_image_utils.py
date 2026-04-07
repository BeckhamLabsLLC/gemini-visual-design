"""Tests for shared image reading utility."""

import pytest

from gemini_visual_mcp.image_utils import MIME_MAP, read_image


class TestReadImage:
    """Tests for read_image function."""

    def test_read_png(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        data, mime = read_image(str(img))
        assert data == b"\x89PNG\r\n\x1a\n"
        assert mime == "image/png"

    def test_read_jpg(self, tmp_path):
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff")
        data, mime = read_image(str(img))
        assert data == b"\xff\xd8\xff"
        assert mime == "image/jpeg"

    def test_read_jpeg(self, tmp_path):
        img = tmp_path / "test.jpeg"
        img.write_bytes(b"jpeg-data")
        _, mime = read_image(str(img))
        assert mime == "image/jpeg"

    def test_read_webp(self, tmp_path):
        img = tmp_path / "test.webp"
        img.write_bytes(b"webp-data")
        _, mime = read_image(str(img))
        assert mime == "image/webp"

    def test_read_gif(self, tmp_path):
        img = tmp_path / "test.gif"
        img.write_bytes(b"GIF89a")
        _, mime = read_image(str(img))
        assert mime == "image/gif"

    def test_read_bmp(self, tmp_path):
        img = tmp_path / "test.bmp"
        img.write_bytes(b"BM")
        _, mime = read_image(str(img))
        assert mime == "image/bmp"

    def test_unknown_extension_raises(self, tmp_path):
        img = tmp_path / "test.tiff"
        img.write_bytes(b"tiff-data")
        with pytest.raises(ValueError, match="Unsupported image format"):
            read_image(str(img))

    def test_no_extension_raises(self, tmp_path):
        img = tmp_path / "noext"
        img.write_bytes(b"data")
        with pytest.raises(ValueError, match="Unsupported image format"):
            read_image(str(img))

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError, match="Image not found"):
            read_image("/nonexistent/image.png")

    def test_returned_bytes_match(self, tmp_path):
        content = b"\x00\x01\x02\x03" * 100
        img = tmp_path / "binary.png"
        img.write_bytes(content)
        data, _ = read_image(str(img))
        assert data == content


class TestMimeMap:
    """Tests for the MIME_MAP constant."""

    def test_all_expected_extensions(self):
        assert ".png" in MIME_MAP
        assert ".jpg" in MIME_MAP
        assert ".jpeg" in MIME_MAP
        assert ".webp" in MIME_MAP
        assert ".gif" in MIME_MAP
        assert ".bmp" in MIME_MAP
