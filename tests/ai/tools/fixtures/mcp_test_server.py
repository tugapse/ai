"""
Minimal stdio MCP server used by the MCPBridge tests.

Run as a subprocess by the tests (``python mcp_test_server.py``), exactly like
real servers configured in mcp_config.json (e.g. ``npx @playwright/mcp``).
"""

import base64

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.utilities.types import Image

server = MCPServer("jarvis-test-server", log_level="CRITICAL")

# 1x1 transparent PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@server.tool()
def echo(text: str) -> str:
    """Return the text unchanged."""
    return text


@server.tool()
def add(a: int, b: int) -> str:
    """Add two integers."""
    return f"{a}+{b}={a + b} ({type(a).__name__},{type(b).__name__})"


@server.tool()
def scale(value: float, factor: float = 2.0) -> str:
    """Multiply a number by a factor."""
    return f"{value * factor}"


@server.tool()
def flag(enabled: bool) -> str:
    """Report a boolean flag."""
    return f"enabled={enabled} ({type(enabled).__name__})"


@server.tool()
def join(items: list[str], sep: str = ",") -> str:
    """Join a list of strings."""
    return sep.join(items)


@server.tool()
def describe(config: dict) -> str:
    """Describe a JSON object."""
    return "keys=" + ",".join(sorted(config))


@server.tool()
def fail(message: str) -> str:
    """Always fails with the given message."""
    raise ToolError(message)


@server.tool()
def multi() -> list[str]:
    """Return several text parts."""
    return ["part one", "part two"]


@server.tool()
def screenshot() -> Image:
    """Return a tiny PNG image (like Playwright's browser_take_screenshot)."""
    return Image(data=_PNG, format="png")


@server.tool()
def tabs(action: str, command: str = "") -> str:
    """Has parameters named like the gateway's own (like Playwright's browser_tabs)."""
    return f"tabs action={action} command={command}"


@server.tool()
def noisy() -> str:
    """Writes to stderr (like servers that log there) and returns."""
    import sys
    print("NOISY-STDERR-LINE", file=sys.stderr, flush=True)
    return "done"


if __name__ == "__main__":
    import sys
    print("TEST SERVER STARTED ON STDIO", file=sys.stderr, flush=True)
    server.run("stdio")
