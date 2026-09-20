"""The real error map.

The previous TestErrorHandling patched _handle_tool and then asserted the
patch raised, which tested unittest.mock rather than the server. The mapping
in _dispatch had zero coverage.
"""

import json
import textwrap

import pytest

from gemini_visual_mcp.gemini_client import (
    GeminiAuthError,
    GeminiClientError,
    GeminiContentPolicyError,
    GeminiQuotaError,
)
from gemini_visual_mcp.paths import ProjectRootError
from gemini_visual_mcp.prompt_engine import PromptValidationError


def _payload(result):
    assert len(result) == 1
    assert result[0].type == "text"
    return json.loads(result[0].text)


class TestDispatchErrorMapping:
    @pytest.mark.parametrize(
        "exc,expected_type",
        [
            (PromptValidationError("too short"), "validation"),
            (GeminiAuthError("bad key"), "auth_error"),
            (GeminiQuotaError("slow down"), "quota_error"),
            (GeminiContentPolicyError("refused"), "content_policy"),
            (GeminiClientError("upstream boom"), "api_error"),
            (ProjectRootError("no root"), "no_project_root"),
            (FileNotFoundError("missing.png"), "file_not_found"),
            (ValueError("bad argument"), "invalid_argument"),
        ],
    )
    @pytest.mark.asyncio
    async def test_error_types(self, server, monkeypatch, exc, expected_type):
        async def boom(name, args):
            raise exc

        monkeypatch.setattr(server, "_handle_tool", boom)
        payload = _payload(await server._dispatch("generate_image", {}))
        assert payload["type"] == expected_type
        assert payload["error"]

    @pytest.mark.asyncio
    async def test_quota_is_distinguishable_from_generic_api_error(self, server, monkeypatch):
        """Three error subclasses used to collapse into one 'api_error'."""

        async def boom(name, args):
            raise GeminiQuotaError("quota")

        monkeypatch.setattr(server, "_handle_tool", boom)
        payload = _payload(await server._dispatch("generate_image", {}))
        assert payload["type"] != "api_error"

    @pytest.mark.asyncio
    async def test_unexpected_errors_are_reraised(self, server, monkeypatch, caplog):
        async def boom(name, args):
            raise KeyError("a bug")

        monkeypatch.setattr(server, "_handle_tool", boom)
        with pytest.raises(KeyError):
            await server._dispatch("generate_image", {})
        assert "Unexpected error" in caplog.text

    @pytest.mark.asyncio
    async def test_success_serializes_non_json_types(self, server, monkeypatch):
        from pathlib import Path

        async def ok(name, args):
            return {"path": Path("/tmp/x.png")}

        monkeypatch.setattr(server, "_handle_tool", ok)
        payload = _payload(await server._dispatch("generate_image", {}))
        assert payload["path"] == "/tmp/x.png"

    @pytest.mark.asyncio
    async def test_unknown_tool_reports_as_invalid_argument(self, server):
        payload = _payload(await server._dispatch("no_such_tool", {}))
        assert payload["type"] == "invalid_argument"
        assert "Unknown tool" in payload["error"]


class TestToolRegistrationDrift:
    def test_advertised_tools_match_routed_tools(self, server):
        """A tool in the schema that _handle_tool can't route is a dead end."""
        import ast
        import inspect

        advertised = {t.name for t in server.tool_definitions()}

        source = textwrap.dedent(inspect.getsource(server._handle_tool))
        routed = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name):
                if node.left.id == "name":
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant):
                            routed.add(comparator.value)

        assert advertised == routed, (
            f"advertised but unrouted: {advertised - routed}; "
            f"routed but unadvertised: {routed - advertised}"
        )
