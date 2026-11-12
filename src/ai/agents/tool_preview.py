"""
Human-readable previews of tool calls that need approval (HIL).

Shared by the chat UI permission box and the classic console prompt.
Returns ANSI-colored lines.
"""

import os
from typing import Any, Dict, List

RESET = "\033[0m"
BOLD = "\033[1m"
GREY = "\033[38;5;245m"
RED = "\033[38;5;167m"
GREEN = "\033[38;5;108m"

MAX_PREVIEW_LINES = 8
MAX_LINE_LEN = 110


def _clip(line: str) -> str:
    line = line.rstrip("\n").replace("\t", "    ")
    return line if len(line) <= MAX_LINE_LEN else line[: MAX_LINE_LEN - 1] + "…"


def _block(text: str, prefix: str, color: str, limit: int = MAX_PREVIEW_LINES) -> List[str]:
    lines = str(text or "").splitlines() or [""]
    out = [f"    {color}{prefix} {_clip(line)}{RESET}" for line in lines[:limit]]
    if len(lines) > limit:
        out.append(f"    {GREY}… {len(lines) - limit} more line{'s' if len(lines) - limit != 1 else ''}{RESET}")
    return out


def _target(params: Dict[str, Any]) -> str:
    return str(params.get("path") or params.get("filepath") or params.get("location") or "@ROOT")


def describe_tool_request(tool: str, params: Dict[str, Any]) -> List[str]:
    """Lines describing what a gated tool call is about to do."""
    params = params if isinstance(params, dict) else {}
    label = lambda name: f"  {GREY}{name:<8}{RESET}"
    lines = [f"{label('tool')}{BOLD}{tool}{RESET}"]

    if tool == "execute_command":
        lines.append(f"{label('command')}{params.get('command', '')}")
        lines.append(f"{label('in')}{_target(params)}")
        return lines

    if tool == "write_file":
        path = _target(params)
        content = str(params.get("content") or "")
        exists = os.path.exists(path.replace("@ROOT/", "").replace("@ROOT", ".") or ".")
        n = len(content.splitlines())
        lines.append(f"{label('file')}{path}  {GREY}({'overwrite' if exists else 'new file'} · {n} line{'s' if n != 1 else ''}){RESET}")
        lines += _block(content, "+", GREEN)
        return lines

    if tool == "patch_file":
        lines.append(f"{label('file')}{_target(params)}")
        lines += _block(params.get("search", ""), "-", RED, MAX_PREVIEW_LINES // 2 + 2)
        lines += _block(params.get("replace", ""), "+", GREEN, MAX_PREVIEW_LINES // 2 + 2)
        return lines

    if tool == "delete_file":
        lines.append(f"{label('delete')}{RED}{_target(params)}{RESET}")
        return lines

    # Generic tool (e.g. MCP): show the arguments
    for key, value in list(params.items())[:6]:
        lines.append(f"{label(str(key)[:8])}{_clip(str(value))}")
    return lines
