"""
Web tools: search the web and read pages as clean text, without launching a browser.

Enabled by default; disable with "TOOLS_WEB_ENABLED": false in config.json.
"""

from ai.modules.base_module import ToolModule
from ai.modules.tools_web.tools import web_search, web_read

TOOLS = [web_search, web_read]


def create_module() -> ToolModule:
    return ToolModule("tools_web", TOOLS, description="Web tools: search the web and read pages as clean text, without launching a browser.")
