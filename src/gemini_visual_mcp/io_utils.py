"""Atomic file writes.

A crash midway through a write used to leave truncated JSON behind, and
load_profile would then silently return None - losing a style profile the
user had built up. Write to a temp file in the same directory, then rename.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _umask() -> int:
    current = os.umask(0)
    os.umask(current)
    return current


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # mkstemp creates 0600; generated assets and profiles should follow
        # the user's umask like an ordinary file write would.
        os.chmod(tmp, 0o666 & ~_umask())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def atomic_write_json(path: Path, payload: Any, indent: int = 2) -> Path:
    text = json.dumps(payload, indent=indent, default=str)
    return atomic_write_bytes(path, text.encode("utf-8"))
