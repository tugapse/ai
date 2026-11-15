"""
Human-readable previews of tool calls that need approval (HIL).

Shared by the chat UI permission box, the classic console prompt and the web
UI (which strips the colors). Returns ANSI-colored lines.
"""

import difflib
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple

RESET = "\033[0m"
BOLD = "\033[1m"
GREY = "\033[38;5;245m"
RED = "\033[38;5;167m"
GREEN = "\033[38;5;108m"

MAX_PREVIEW_LINES = 8
MAX_DIFF_LINES = 12
MAX_LINE_LEN = 110


def _clip(line: str, limit: int = MAX_LINE_LEN) -> str:
    line = line.rstrip("\n").replace("\t", "    ")
    return line if len(line) <= limit else line[: limit - 1] + "…"


def _more(count: int) -> str:
    return f"    {GREY}… {count} more line{'s' if count != 1 else ''}{RESET}"


def _block(text: str, prefix: str, color: str, limit: int = MAX_PREVIEW_LINES) -> List[str]:
    lines = str(text or "").splitlines() or [""]
    out = [f"    {color}{prefix} {_clip(line)}{RESET}" for line in lines[:limit]]
    if len(lines) > limit:
        out.append(_more(len(lines) - limit))
    return out


def _target(params: Dict[str, Any]) -> str:
    return str(params.get("path") or params.get("filepath") or params.get("location") or "@ROOT")


def _shown_path(path: str) -> str:
    """Paths are relative to the AI root: '@ROOT/' adds nothing on screen."""
    return path.replace("@ROOT/", "") if path != "@ROOT" else "."


def _width() -> int:
    try:
        return max(40, min(shutil.get_terminal_size((100, 24)).columns, 160))
    except Exception:
        return 100


def diff_lines(search: str, replace: str, limit: int = MAX_DIFF_LINES) -> List[str]:
    """Only the lines a patch changes, with one line of context around each change."""
    old = str(search or "").splitlines()
    new = str(replace or "").splitlines()
    out: List[str] = []
    for group in difflib.SequenceMatcher(None, old, new, autojunk=False).get_grouped_opcodes(1):
        if out:
            out.append(f"    {GREY}  ⋮{RESET}")
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                out += [f"    {GREY}  {_clip(line)}{RESET}" for line in old[i1:i2]]
                continue
            out += [f"    {RED}- {_clip(line)}{RESET}" for line in old[i1:i2]]
            out += [f"    {GREEN}+ {_clip(line)}{RESET}" for line in new[j1:j2]]
    if not out:
        return [f"    {GREY}(no change){RESET}"]
    if len(out) > limit:
        out = out[:limit] + [_more(len(out) - limit)]
    return out


def _split_chain(command: str) -> List[str]:
    """Splits 'a && b || c' at the top-level operators (not inside quotes); each part keeps its operator."""
    parts, current, quote, i = [], "", "", 0
    while i < len(command):
        ch = command[i]
        if quote:
            if ch == quote:
                quote = ""
            elif ch == "\\" and quote == '"' and i + 1 < len(command):
                current += ch + command[i + 1]
                i += 2
                continue
        elif ch in "'\"":
            quote = ch
        elif command.startswith(" && ", i) or command.startswith(" || ", i):
            parts.append(current.strip())
            current = command[i + 1:i + 3]
            i += 3
            continue
        current += ch
        i += 1
    parts.append(current.strip())
    return [p for p in parts if p]


def command_lines(command: str, width: Optional[int] = None) -> List[str]:
    """A shell command laid out for reading: one '&&' step per line, long steps wrapped with an indent."""
    import textwrap

    width = (width or _width()) - 6
    command = " ".join(str(command or "").split())
    if len(command) <= width:
        return [f"    {command}"]
    lines = []
    for part in _split_chain(command):
        wrapped = textwrap.wrap(part, width, subsequent_indent="    ", break_long_words=True,
                                break_on_hyphens=False) or [part]
        lines += [f"    {line}" for line in wrapped]
    return lines


def request_summary(tool: str, params: Dict[str, Any]) -> Tuple[str, List[str]]:
    """(subject, body lines): what a gated call acts on, and the preview of what it will do."""
    params = params if isinstance(params, dict) else {}

    if tool == "execute_command":
        target = _target(params)
        subject = f"in {_shown_path(target)}" if target != "@ROOT" else ""
        return subject, command_lines(params.get("command", ""))

    if tool == "write_file":
        path = _target(params)
        content = str(params.get("content") or "")
        exists = os.path.exists(path.replace("@ROOT/", "").replace("@ROOT", ".") or ".")
        n = len(content.splitlines())
        subject = f"{_shown_path(path)}  {GREY}({'overwrite' if exists else 'new file'} · {n} line{'s' if n != 1 else ''}){RESET}"
        return subject, _block(content, "+", GREEN)

    if tool == "patch_file":
        return _shown_path(_target(params)), diff_lines(params.get("search", ""), params.get("replace", ""))

    if tool == "delete_file":
        return f"{RED}{_shown_path(_target(params))}{RESET}", []

    # Generic tool (e.g. MCP): show the arguments
    items = list(params.items())
    lines = [f"    {GREY}{str(key):<10}{RESET}{_clip(str(value), MAX_LINE_LEN - 14)}" for key, value in items[:6]]
    if len(items) > 6:
        lines.append(f"    {GREY}… {len(items) - 6} more{RESET}")
    return "", lines


def always_scope(tool: str, params: Dict[str, Any]) -> Optional[str]:
    """What an "always" answer would cover, or None when it only covers this call."""
    from ai.agents.approval_scope import describe, rule_for
    from ai.tools.mcp_admin_tools import ALWAYS_GATED

    rule = rule_for(tool, params if isinstance(params, dict) else {}, ALWAYS_GATED)
    return describe(rule) if rule else None


def describe_tool_request(tool: str, params: Dict[str, Any]) -> List[str]:
    """Lines describing what a gated tool call is about to do, and what "always" would cover."""
    subject, body = request_summary(tool, params)
    lines = [f"  {BOLD}{tool}{RESET}" + (f"  {subject}" if subject else ""), *body]
    scope = always_scope(tool, params)
    lines.append(f"  {GREY}always = {scope or 'this call only'}{RESET}")
    return lines
