"""Gemini Visual Design MCP Server.

Integrates Google Gemini's visual AI capabilities into the development workflow
with prompt enhancement, project-aware style profiles, and iterative editing.
"""

__version__ = "1.0.0"


def main():
    """Entry point for the MCP server."""
    from .server import main as _main

    _main()


__all__ = ["main", "__version__"]
