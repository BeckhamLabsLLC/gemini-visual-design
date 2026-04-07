"""Asset manager for temp previews, metadata sidecars, and project saves."""

import itertools
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .config import PREVIEW_DIR, PREVIEW_MAX_AGE_DAYS

logger = logging.getLogger(__name__)

_counter = itertools.count()


def _ensure_preview_dir() -> Path:
    """Ensure the preview directory exists."""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return PREVIEW_DIR


def _generate_filename(prefix: str, mime_type: str) -> str:
    """Generate a unique filename with timestamp and counter."""
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
    }
    ext = ext_map.get(mime_type, ".bin")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    seq = next(_counter)
    return f"{prefix}_{timestamp}_{seq}{ext}"


def save_generated(
    data: bytes,
    mime_type: str,
    metadata: dict,
    prefix: str = "gen",
) -> Path:
    """Save generated content to preview directory with metadata sidecar.

    Args:
        data: Raw bytes of the generated content
        mime_type: MIME type (image/png, video/mp4, etc.)
        metadata: Dict with prompt, model, params, etc.
        prefix: Filename prefix (gen, edit, video, etc.)

    Returns:
        Path to the saved file in the preview directory
    """
    preview_dir = _ensure_preview_dir()
    filename = _generate_filename(prefix, mime_type)
    file_path = preview_dir / filename

    # Save the content
    with open(file_path, "wb") as f:
        f.write(data)

    # Save metadata sidecar
    meta_path = preview_dir / f"{filename}.meta.json"
    meta = {
        "timestamp": datetime.now().isoformat(),
        "mime_type": mime_type,
        "size_bytes": len(data),
        "filename": filename,
        **metadata,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    logger.info(f"Saved generated asset: {file_path} ({len(data)} bytes)")
    return file_path


def list_generated() -> list[dict]:
    """List all generated assets in preview directory with metadata.

    Returns list of dicts with: name, type, size, timestamp, prompt, model
    """
    preview_dir = _ensure_preview_dir()
    results = []

    for meta_file in sorted(preview_dir.glob("*.meta.json")):
        try:
            with open(meta_file) as f:
                meta = json.load(f)

            # Check that the actual file still exists
            asset_name = meta.get("filename", meta_file.stem)
            asset_path = preview_dir / asset_name
            if not asset_path.exists():
                continue

            results.append(
                {
                    "name": asset_name,
                    "path": str(asset_path),
                    "mime_type": meta.get("mime_type", "unknown"),
                    "size_bytes": meta.get("size_bytes", 0),
                    "timestamp": meta.get("timestamp", ""),
                    "prompt": meta.get("prompt", ""),
                    "enhanced_prompt": meta.get("enhanced_prompt", ""),
                    "model": meta.get("model", ""),
                    "template": meta.get("template", ""),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue

    return results


def save_to_project(temp_path: str, dest_dir: str, filename: str) -> Path:
    """Copy a generated asset from preview to project directory.

    Args:
        temp_path: Path to the file in preview directory
        dest_dir: Target directory in the project
        filename: Desired filename (must not escape dest_dir)

    Returns:
        Path to the saved file in the project

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If filename would resolve outside dest_dir.
    """
    source = Path(temp_path)
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {temp_path}")

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    target = (dest / filename).resolve()
    if dest_resolved not in target.parents and target != dest_resolved:
        raise ValueError(
            f"Filename {filename!r} resolves outside destination directory {dest_dir!r}"
        )

    shutil.copy2(source, target)

    # Also copy metadata if it exists. The same containment rules apply so a
    # malicious filename can't smuggle a sidecar into a parent directory.
    meta_source = source.parent / f"{source.name}.meta.json"
    if meta_source.is_file():
        meta_target = (dest / f"{filename}.meta.json").resolve()
        if dest_resolved not in meta_target.parents and meta_target != dest_resolved:
            raise ValueError(
                f"Sidecar for {filename!r} resolves outside destination directory"
            )
        shutil.copy2(meta_source, meta_target)

    logger.info(f"Saved asset to project: {target}")
    return target


def cleanup_old(max_age_days: int = PREVIEW_MAX_AGE_DAYS) -> int:
    """Remove preview files older than max_age_days.

    Returns the number of files removed.
    """
    preview_dir = _ensure_preview_dir()
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0

    for f in preview_dir.iterdir():
        if f.is_file():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1
            except OSError:
                continue

    if removed > 0:
        logger.info(f"Cleaned up {removed} old preview files")
    return removed


def get_preview_dir() -> str:
    """Return the preview directory path."""
    return str(_ensure_preview_dir())
