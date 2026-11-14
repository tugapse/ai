"""
Shell tool: run non-interactive commands in the project.

Enabled by default; disable with "TOOLS_SHELL_ENABLED": false in config.json.
"""

from ai.modules.base_module import ToolModule
from ai.modules.tools_shell.tools import execute_command

TOOLS = [execute_command]


def create_module() -> ToolModule:
    return ToolModule("tools_shell", TOOLS, category="shell",
                      description="Run non-interactive shell commands in the project (tests, builds, git, scripts).")
