"""
Search tools: find files and content across the project, or inside one file.

Enabled by default; disable with "TOOLS_SEARCH_ENABLED": false in config.json.
"""

from ai.modules.base_module import ToolModule
from ai.modules.tools_search.tools import smart_search, grep_file

TOOLS = [smart_search, grep_file]


def create_module() -> ToolModule:
    return ToolModule("tools_search", TOOLS, description='Search tools: find files and content across the project, or inside one file.')
