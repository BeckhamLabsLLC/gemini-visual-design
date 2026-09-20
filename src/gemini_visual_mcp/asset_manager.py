"""Asset manager for temp previews, metadata sidecars, and project saves."""

import json
import logging
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from .config import PREVIEW_DIR, PREVIEW_MAX_AGE_DAYS
from .io_utils import atomic_write_bytes, atomic_write_json

logger = logging.getLogger(__name__)


def _ensure_preview_dir() -> Path:
    """Ensure the preview directory exists."""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return PREVIEW_DIR


def _generate_filename(prefix: str, mime_type: str) -> str:
    """Generate a unique filename.

    Uses a random suffix rather than a process-local counter: two server
    processes generating in the same second used to produce identical names
    and silently overwrite each other.
    """
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
    }
    ext = ext_map.get(mime_type, ".bin")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"


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
    atomic_write_bytes(file_path, data)

    # Save metadata sidecar
    meta_path = preview_dir / f"{filename}.meta.json"
    meta = {
        "timestamp": datetime.now().isoformat(),
        "mime_type": mime_type,
        "size_bytes": len(data),
        "filename": filename,
        **metadata,
    }
    atomic_write_json(meta_path, meta)

    logger.info(f"Saved generated asset: {file_path} ({len(data)} bytes)")
    return file_path


def list_generated() -> list[dict]:
    """List all generated assets in preview directory with metadata.

    Returns list of dicts with: name, type, size, timestamp, prompt, model
    """
    preview_dir = _ensure_preview_dir()
    results = []

    for meta_file in preview_dir.glob("*.meta.json"):
        try:
            with open(meta_file) as f:
                meta = json.load(f)

            # Check that the actual file still exists
            asset_name = meta.get("filename") or meta_file.name.removesuffix(".meta.json")
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

    results.sort(key=lambda r: r.get("timestamp", ""))
    return results


def save_to_project(
    temp_path: str,
    dest_dir: str,
    filename: str,
    project_root: str | None = None,
) -> Path:
    """Copy a generated asset from preview into the project.

    Args:
        temp_path: Path to the file in the preview directory
        dest_dir: Target directory; relative paths resolve against project_root
        filename: A bare filename - no separators, no traversal
        project_root: If given, dest_dir must resolve inside it

    Returns:
        Path to the saved file

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If filename or dest_dir is unacceptable.
    """
    source = Path(temp_path)
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {temp_path}")

    # One check kills "..", ".", "sub/x.png", "/abs/x" and "".
    if filename in ("", ".", "..") or Path(filename).name != filename:
        raise ValueError(
            f"filename must be a bare filename with no path separators, got {filename!r}"
        )

    dest = Path(dest_dir).expanduser()
    if project_root:
        root = Path(project_root).expanduser().resolve()
        if not dest.is_absolute():
            dest = root / dest
        dest_resolved = dest.resolve()
        if dest_resolved != root and root not in dest_resolved.parents:
            raise ValueError(
                f"destination_dir {dest_dir!r} resolves outside the project "
                f"({dest_resolved}). Choose a directory inside {root}."
            )
    else:
        dest_resolved = dest.resolve()

    target = dest_resolved / filename
    if target.exists():
        raise ValueError(
            f"{target} already exists. Choose a different filename so an "
            "existing asset isn't overwritten."
        )

    # Only create directories once the request is known to be acceptable.
    dest_resolved.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

    meta_source = source.parent / f"{source.name}.meta.json"
    if meta_source.is_file():
        shutil.copy2(meta_source, dest_resolved / f"{filename}.meta.json")

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
