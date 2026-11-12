"""
Notification tool: desktop notifications so the agent can tell you when something is done.

Enabled by default; disable with "TOOLS_NOTIFY_ENABLED": false in config.json.
"""

from ai.modules.base_module import ToolModule
from ai.modules.tools_notify.tools import send_notification

TOOLS = [send_notification]


def create_module() -> ToolModule:
    return ToolModule("tools_notify", TOOLS, description="Notification tool: desktop notifications so the agent can tell you when something is done.")
