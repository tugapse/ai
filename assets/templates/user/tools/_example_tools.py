"""
Example of user tools. Files starting with '_' are not loaded: copy this one to a name such as
git_tools.py to enable it.

Every tool must belong to a ToolCategory. The agent first sees only the category's name and
description. It calls open_tools to unlock the category, and only then reads the tools' docstrings.
Rules checked at load time:
  - name: 2-40 lowercase letters, digits or '_', unique (built-in ones: filesystem, search,
    shell, web, notify, knowledge, memory, plus one per MCP server);
  - description: one line of at most 120 characters;
  - each tool: marked with @tool, with a docstring, and an 'Args:' section when it takes
    parameters (format: 'name (type): description');
  - a tool name may belong to only one category, and every @tool function in the file must be in
    a category.
Add the tool names to a pipeline agent's "tools" list to give them to that agent.
"""

import subprocess

from ai.tools import ToolCategory, tool
from ai.tools.base import resolve_path


@tool
def git_status(path: str = "@ROOT") -> dict:
    """
    Shows the git status of the project (changed, staged and untracked files).

    Args:
        path (string, optional): Repository folder. Defaults to the project root.

    Returns:
        output: the short git status, or an error.
    """
    try:
        cwd = resolve_path({"path": path})
        out = subprocess.run(["git", "status", "--short", "--branch"], cwd=cwd,
                             capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return {"status": "FAILED", "error": out.stderr.strip()}
        return {"status": "SUCCESS", "output": out.stdout}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


class GitTools(ToolCategory):
    name = "git"
    description = "Inspect the git repository of the project: status of changed files."

    def get_category_tools(self):
        return [git_status]
