"""Wiring tests against a REAL mcp Server, not a mock.

Every other test in this suite patches gemini_visual_mcp.server.Server, which
means none of them can see whether a handler is actually registered. A
refactor once stranded the @call_tool registration after a `return`, so every
tool call failed with "Method not found" while all 177 unit tests passed.
These tests exist to make that impossible.
"""

import mcp.types as types
import pytest

from gemini_visual_mcp import __version__
from gemini_visual_mcp.server import GeminiVisualDesignServer


@pytest.fixture
def real_server(monkeypatch):
    """A server built on an unmocked mcp Server."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    return GeminiVisualDesignServer()


class TestHandlerRegistration:
    def test_list_tools_handler_is_registered(self, real_server):
        assert types.ListToolsRequest in real_server._server.request_handlers

    def test_call_tool_handler_is_registered(self, real_server):
        """Stranding this registration made every tool call unreachable."""
        assert types.CallToolRequest in real_server._server.request_handlers

    def test_server_reports_the_plugin_version(self, real_server):
        """It defaulted to the mcp library's version, which is misleading."""
        assert real_server._server.version == __version__

    def test_server_is_named_for_the_plugin(self, real_server):
        assert real_server._server.name == "gemini-visual-design"


class TestAdvertisedSchema:
    def test_nine_tools_are_advertised(self, real_server):
        assert len(real_server.tool_definitions()) == 9

    def test_every_tool_schema_is_valid_json_schema(self, real_server):
        import jsonschema

        for tool in real_server.tool_definitions():
            jsonschema.Draft7Validator.check_schema(tool.inputSchema)

    def test_generate_image_advertises_current_tiers(self, real_server):
        tool = next(t for t in real_server.tool_definitions() if t.name == "generate_image")
        props = tool.inputSchema["properties"]
        assert props["model"]["enum"] == ["draft", "fast", "pro", "auto"]
        assert "resolution" in props
        # A hardcoded default here would stop a template from ever winning.
        assert "default" not in props["aspect_ratio"]

    @pytest.mark.asyncio
    async def test_list_tools_handler_returns_the_definitions(self, real_server):
        handler = real_server._server.request_handlers[types.ListToolsRequest]
        result = await handler(types.ListToolsRequest(method="tools/list"))
        assert len(result.root.tools) == 9
