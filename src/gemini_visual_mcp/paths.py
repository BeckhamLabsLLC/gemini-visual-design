"""Resolution of the user's project root.

Claude Code exports CLAUDE_PROJECT_DIR to MCP server subprocesses. The
`cwd` key in .mcp.json is currently ignored by Claude Code
(anthropics/claude-code#17565), so the process inherits the project
directory as its cwd - correct today, but not something to rely on.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# The plugin's own root, i.e. the parent of src/gemini_visual_mcp/.
PLUGIN_ROOT = Path(__file__).resolve().parents[2]


class ProjectRootError(RuntimeError):
    """The user's project root could not be determined."""


def _candidate(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_dir():
        logger.warning("%s is set to %r which is not a directory; ignoring.", name, raw)
        return None
    return path.resolve()


def resolve_project_root(strict: bool = False) -> tuple[Path, str]:
    """Resolve the user's project root.

    Precedence:
      1. GEMINI_VISUAL_PROJECT_DIR - namespaced user override.
      2. CLAUDE_PROJECT_DIR - set by Claude Code for MCP subprocesses.
      3. os.getcwd() - fallback for non-Claude MCP hosts.

    Returns (root, source). With strict=True, raises ProjectRootError when the
    only answer is a cwd that sits inside the plugin's own tree - that is the
    "server started in its own source directory" failure mode, and writing a
    style profile or an asset there is never what the user meant.

    PROJECT_DIR is deliberately NOT consulted. It is an unnamespaced name that
    build tooling commonly sets for its own purposes.
    """
    for name in ("GEMINI_VISUAL_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        found = _candidate(name)
        if found is not None:
            return found, name

    cwd = Path.cwd().resolve()
    inside_plugin = cwd == PLUGIN_ROOT or PLUGIN_ROOT in cwd.parents

    if inside_plugin:
        message = (
            "Could not determine your project directory: no "
            "CLAUDE_PROJECT_DIR or GEMINI_VISUAL_PROJECT_DIR is set, and the "
            f"working directory ({cwd}) is inside the plugin itself. Set "
            "GEMINI_VISUAL_PROJECT_DIR to your project root and restart."
        )
        if strict:
            raise ProjectRootError(message)
        logger.warning("%s Proceeding without a project profile.", message)

    return cwd, "cwd"
