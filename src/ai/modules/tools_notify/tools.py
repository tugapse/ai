"""Notification tool: desktop notifications so the agent can tell you when something is done."""

import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from ai.tools.base import tool

URGENCY = ("low", "normal", "critical")


def _notify_command(title: str, message: str, urgency: str) -> Optional[List[str]]:
    """Builds the platform command (argument list, never a shell string)."""
    if sys.platform.startswith("linux") and shutil.which("notify-send"):
        return ["notify-send", "--app-name=JARVIS", f"--urgency={urgency}", title, message]
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f"display notification {_applescript_str(message)} with title {_applescript_str(title)}"
        return ["osascript", "-e", script]
    return None


def _applescript_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


@tool
def send_notification(**kwargs) -> Dict[str, Any]:
    """
    Show a desktop notification to the user. Use it only when the user is waiting for something,
    e.g. a long task finished or you need their attention. Do not use it for normal replies.

    Args:
        message (string): The notification text, one or two short sentences.
        title (string, optional): Short title. Default 'JARVIS'.
        urgency (string, optional): 'low', 'normal' or 'critical'. Default 'normal'.

    Returns:
        status SUCCESS and method (how it was shown), or status FAILED with the reason.
    """
    message = str(kwargs.get("message") or kwargs.get("text") or "").strip()
    if not message:
        return {"status": "FAILED", "error": "No message provided."}
    title = str(kwargs.get("title") or "JARVIS").strip()[:100]
    message = message[:1000]
    urgency = str(kwargs.get("urgency") or "normal").strip().lower()
    if urgency not in URGENCY:
        urgency = "normal"

    command = _notify_command(title, message, urgency)
    if command is None:
        # No desktop notifier: ring the terminal bell so the user still gets a cue.
        try:
            sys.__stdout__.write("\a")
            sys.__stdout__.flush()
        except Exception:
            pass
        return {"status": "SUCCESS", "method": "terminal-bell", "note": "No desktop notifier available on this system."}

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
    except Exception as e:
        return {"status": "FAILED", "error": f"Notification failed: {e}"}
    if result.returncode != 0:
        return {"status": "FAILED", "error": (result.stderr or result.stdout or f"exit code {result.returncode}").strip()}
    return {"status": "SUCCESS", "method": command[0]}
