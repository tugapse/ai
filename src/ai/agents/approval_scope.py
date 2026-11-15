"""
What an "always" answer to a permission request covers.

Answering "always" used to approve the whole tool for the rest of the session: one "always" on
``execute_command: ls`` also approved ``rm -rf``. Now it covers:

- shell commands: the same program and sub-command (``git status`` → every ``git status ...``, but
  not ``git push``); a command approved without a sub-command (``ls -la``) covers that program;
  Commands with shell operators (``;``, ``&&``, ``|``, ``>``, ``$(``...) are never remembered;
- file tools: the same tool in the same folder (and folders below it);
- tools that must always ask (``enable_mcp_server``): never remembered;
- anything else: the whole tool, as before.

Rules are plain strings so they can be saved with the session: ``"tool"`` (whole tool),
``"tool|cmd:git status"``, ``"tool|dir:/abs/folder"``.
"""
import os
import re
import shlex
from typing import Any, Dict, Iterable, Optional

SHELL_TOOLS = ("execute_command",)
FILE_TOOLS = ("write_file", "patch_file", "delete_file")
_SHELL_OPERATORS = re.compile(r"[;&|<>`\n]|\$\(")
_SUBCOMMAND = re.compile(r"^[A-Za-z][\w.:-]*$")


def _path(params: Dict[str, Any]) -> Optional[str]:
    raw = params.get("path") or params.get("filepath")
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw = raw.strip()
    if raw.startswith("@ROOT"):
        raw = "." + raw[len("@ROOT"):]
    return os.path.normpath(os.path.abspath(raw))


def command_prefix(command: Any) -> Optional[str]:
    """``git status -s`` → ``git status``; ``ls -la`` → ``ls``; None when it can't be remembered."""
    if not isinstance(command, str) or not command.strip() or _SHELL_OPERATORS.search(command):
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens:
        return None
    prefix = [tokens[0]]
    if len(tokens) > 1 and _SUBCOMMAND.match(tokens[1]):
        prefix.append(tokens[1])
    return " ".join(prefix)


def rule_for(tool: str, params: Dict[str, Any], never_remember: Iterable[str] = ()) -> Optional[str]:
    """The rule an "always" answer adds for this call, or None if it can't be remembered."""
    params = params if isinstance(params, dict) else {}
    if tool in never_remember:
        return None
    if tool in SHELL_TOOLS:
        prefix = command_prefix(params.get("command"))
        return f"{tool}|cmd:{prefix}" if prefix else None
    if tool in FILE_TOOLS:
        path = _path(params)
        return f"{tool}|dir:{os.path.dirname(path)}" if path else None
    return tool


def is_allowed(tool: str, params: Dict[str, Any], rules: Iterable[str]) -> bool:
    """True when a remembered rule covers this call."""
    params = params if isinstance(params, dict) else {}
    rules = set(rules)
    if tool in rules:
        return True
    if tool in SHELL_TOOLS:
        prefix = command_prefix(params.get("command"))
        if not prefix:
            return False
        program = prefix.split(" ", 1)[0]
        # "cmd:ls" covers every ls; "cmd:git status" only git status
        return f"{tool}|cmd:{prefix}" in rules or f"{tool}|cmd:{program}" in rules
    if tool in FILE_TOOLS:
        path = _path(params)
        if not path:
            return False
        folder = os.path.dirname(path)
        marker = f"{tool}|dir:"
        for rule in rules:
            if rule.startswith(marker):
                allowed = rule[len(marker):]
                if folder == allowed or folder.startswith(allowed.rstrip(os.sep) + os.sep):
                    return True
    return False


def describe(rule: Optional[str]) -> str:
    """Short text for the user: what "always" will cover."""
    if not rule:
        return "this call only"
    tool, _, scope = rule.partition("|")
    if scope.startswith("cmd:"):
        return f"'{scope[4:]}' commands"
    if scope.startswith("dir:"):
        return f"{tool} in {scope[4:]}"
    return f"every {tool} call"
