#!/usr/bin/env python3
"""Launch the server exactly as .mcp.json does and speak MCP to it.

Makes no API calls and costs nothing. This catches what the unit tests
structurally cannot: they patch mcp's Server, so they cannot see a broken
launch command, an unresolvable dependency, or an unregistered handler.

    python scripts/check_protocol.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def expand(value: str, project: str) -> str:
    return value.replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT)).replace(
        "${CLAUDE_PROJECT_DIR}", project
    )


def main() -> int:
    project = tempfile.mkdtemp(prefix="gvd-protocol-")
    cfg = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["gemini-visual-design"]
    cmd = [expand(cfg["command"], project)] + [expand(a, project) for a in cfg["args"]]

    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update({expand(k, project): expand(v, project) for k, v in cfg.get("env", {}).items()})
    env["CLAUDE_PROJECT_DIR"] = project
    env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    env.setdefault("GEMINI_API_KEY", "not-used-no-calls-are-made")

    print("launch:", " ".join(cmd))
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        env=env, text=True, bufsize=1, cwd=project,
    )

    def rpc(payload):
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        if "id" not in payload:
            return None
        while True:
            line = proc.stdout.readline()
            if not line:
                raise SystemExit("server closed the connection -- check stderr above")
            message = json.loads(line)
            if message.get("id") == payload["id"]:
                return message

    failures = []

    def check(label, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
        if not ok:
            failures.append(label)

    reply = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "check_protocol", "version": "0"}}})
    info = reply.get("result", {}).get("serverInfo", {})
    check("initialize", bool(info), f"{info.get('name')} v{info.get('version')}")

    rpc({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    reply = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = reply.get("result", {}).get("tools", [])
    check("tools/list", len(tools) == 9, f"{len(tools)} tools")

    # A tool call that touches routing and serialization but no paid API.
    reply = rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "get_prompt_templates", "arguments": {"category": "icons"}}})
    ok = "result" in reply
    detail = "" if ok else str(reply.get("error"))
    check("tools/call reaches a handler", ok, detail)

    # Schema validation should reject this before it costs anything.
    reply = rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "generate_image", "arguments": {"prompt": "short"}}})
    check("short prompt rejected", reply.get("result", {}).get("isError") is True)

    proc.stdin.close()
    proc.wait(timeout=30)
    check("clean exit", proc.returncode == 0, f"code {proc.returncode}")

    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        return 1
    print("\nProtocol check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
