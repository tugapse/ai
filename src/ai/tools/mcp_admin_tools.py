"""
Agent tools to see the configured MCP servers and turn one on.

``enable_mcp_server`` always asks the user first (see ``AgentOrchestrator._gatekeeper``): starting a
server runs a program on this machine.
"""
from typing import Any, Callable, Dict, List

from ai.tools.base import tool
from ai.tools.category import ToolCategory
from ai.tools import mcp_config

CATEGORY = "mcp_servers"
ALWAYS_GATED = ("enable_mcp_server",)


class MCPAdminTools(ToolCategory):
    name = CATEGORY
    description = "See the configured MCP servers (browser, GitHub...) and turn one on when you need it."

    def __init__(self, bridge):
        self.bridge = bridge

    def get_category_tools(self) -> List[Callable]:
        return [self.list_mcp_servers, self.enable_mcp_server]

    @tool
    def list_mcp_servers(self, **kwargs) -> Dict[str, Any]:
        """
        Lists the MCP servers in mcp_config.json: whether each is enabled, running (its tool is
        usable now), and what it is for. Disabled servers can be turned on with enable_mcp_server.

        Returns:
            servers: list of {name, enabled, running, auto_allow, description, command}.
        """
        running = set(getattr(self.bridge, "server_schemas", {}) or {})
        rows = mcp_config.describe(getattr(self.bridge, "configured", {}) or {}, running)
        return {"status": "SUCCESS", "servers": rows}

    @tool
    def enable_mcp_server(self, **kwargs) -> Dict[str, Any]:
        """
        Starts a configured MCP server for this run (the user is asked to approve it). Its tool,
        named after the server, is available from your next step.

        Args:
            name (string): Server name from list_mcp_servers, e.g. 'playwright'.
            remember (bool, optional): 'true' to keep it enabled in future runs too. Default 'false'.

        Returns:
            status SUCCESS and the tool name, or FAILED with the reason.
        """
        name = str(kwargs.get("name") or "").strip()
        if not name:
            return {"status": "FAILED", "error": "Missing 'name' (see list_mcp_servers)."}
        result = self.bridge.enable_server(name)
        remember = str(kwargs.get("remember", "false")).strip().lower() in ("1", "true", "yes")
        if result.get("status") == "SUCCESS" and remember:
            try:
                result["saved_to"] = mcp_config.set_enabled(name, True)
            except Exception as e:
                result["note"] = f"Started, but could not save the setting: {e}"
        return result
