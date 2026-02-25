"""Shared image reading utility.

Provides a single read_image function used by analyzer, image_edit,
and video_gen modules to avoid duplicated file-reading logic.
"""

from pathlib import Path

# Extension to MIME type mapping
MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def read_image(image_path: str) -> tuple[bytes, str]:
    """Read an image file and determine its MIME type.

    Args:
        image_path: Path to the image file.

    Returns:
        Tuple of (file bytes, MIME type string).

    Raises:
        FileNotFoundError: If the image file does not exist.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    ext = path.suffix.lower()
    mime_type = MIME_MAP.get(ext, "image/png")

    with open(path, "rb") as f:
        data = f.read()

    return data, mime_type
