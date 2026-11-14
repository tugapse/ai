"""
Tool categories: the contract every group of agent tools implements.

An agent first sees only the categories (name + one-line description). It calls ``open_tools``
to unlock a category, and only then do that category's full tool descriptions enter its prompt.
Built-in tool modules, knowledge, long-term memory, MCP servers and user tools (``<root>/tools``)
are all ``ToolCategory`` objects, validated when registered in the ``ToolRegistry``.

A user tool file::

    from ai.tools import ToolCategory, tool

    @tool
    def git_status(path: str = "@ROOT") -> dict:
        '''
        Shows the git status of the project.

        Args:
            path (string, optional): Repository folder. Defaults to the project root.
        '''
        ...

    class GitTools(ToolCategory):
        name = "git"
        description = "Inspect the repository: status, diff and log"

        def get_category_tools(self):
            return [git_status]
"""

import inspect
import re
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

CATEGORY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_DESCRIPTION_CHARS = 120


class ToolCategoryError(ValueError):
    """A category (or one of its tools) does not follow the ToolCategory contract."""


class ToolCategory(ABC):
    """
    A named group of agent tools.

    Attributes:
        name: Identifier the agent passes to open_tools (lowercase letters, digits, '_').
        description: One line (at most 120 characters) telling the agent what the category is for.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def get_category_tools(self) -> List[Callable]:
        """The @tool functions of this category (may change over time, e.g. once data is loaded)."""

    def describe_open(self) -> Optional[str]:
        """Extra text shown under the category's tools once it is open (e.g. an MCP server's commands)."""
        return None


def tool_name(fn: Callable) -> str:
    return getattr(fn, "__name__", "") or ""


def _has_named_params(fn: Callable) -> bool:
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD) and p.name != "self" for p in params)


def validate_category(category: ToolCategory) -> Dict[str, Callable]:
    """
    Checks a category against the contract.

    Returns:
        {tool_name: callable} of the category's tools.

    Raises:
        ToolCategoryError: naming the category and the rule it breaks.
    """
    label = type(category).__name__
    if not isinstance(category, ToolCategory):
        raise ToolCategoryError(f"{label} is not a ToolCategory.")

    name = category.name
    if not isinstance(name, str) or not CATEGORY_NAME_RE.match(name):
        raise ToolCategoryError(
            f"{label}: invalid category name {name!r} (use 2-40 lowercase letters, digits or '_', starting with a letter).")

    description = category.description
    if not isinstance(description, str) or not description.strip():
        raise ToolCategoryError(f"Category '{name}': a description is required.")
    if "\n" in description.strip() or len(description.strip()) > MAX_DESCRIPTION_CHARS:
        raise ToolCategoryError(
            f"Category '{name}': the description must be one line of at most {MAX_DESCRIPTION_CHARS} characters.")

    try:
        functions = list(category.get_category_tools() or [])
    except Exception as e:
        raise ToolCategoryError(f"Category '{name}': get_category_tools() failed: {e}") from e

    tools: Dict[str, Callable] = {}
    for fn in functions:
        fn_name = tool_name(fn)
        if not callable(fn) or not fn_name:
            raise ToolCategoryError(f"Category '{name}': {fn!r} is not a function.")
        if not getattr(fn, "_is_tool", False):
            raise ToolCategoryError(f"Category '{name}': '{fn_name}' is not marked with @tool.")
        doc = inspect.getdoc(fn) or ""
        if not doc.strip():
            raise ToolCategoryError(f"Category '{name}': '{fn_name}' needs a docstring (the agent reads it).")
        if _has_named_params(fn) and "Args:" not in doc:
            raise ToolCategoryError(f"Category '{name}': '{fn_name}' takes parameters, document them in an 'Args:' section.")
        if fn_name in tools:
            raise ToolCategoryError(f"Category '{name}': tool '{fn_name}' is listed twice.")
        tools[fn_name] = fn
    return tools
