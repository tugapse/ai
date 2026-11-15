import os
import sys
import importlib.util
import inspect
from typing import TYPE_CHECKING, List
import ai.functions as func
from ai.tools.category import ToolCategory, ToolCategoryError

if TYPE_CHECKING:
    from .tool_registry import ToolRegistry


def _categories_in(module) -> List[type]:
    """ToolCategory subclasses defined in this file (not imported into it), in source order."""
    return [
        obj for obj in vars(module).values()
        if inspect.isclass(obj) and issubclass(obj, ToolCategory) and obj is not ToolCategory
        and obj.__module__ == module.__name__ and not inspect.isabstract(obj)
    ]


def _loose_tools(module, categorized: set) -> List[str]:
    """@tool functions defined in this file that no category of it lists."""
    return sorted(
        name for name, obj in vars(module).items()
        if callable(obj) and getattr(obj, "_is_tool", False) and not inspect.isclass(obj)
        and getattr(obj, "__module__", None) == module.__name__ and obj.__name__ not in categorized
    )


def load_and_register_user_tools(registry: "ToolRegistry", user_tools_dir: str):
    """
    Imports every Python file of the user tools directory and registers the ToolCategory
    subclasses defined in it (see ai.tools.category for the contract and an example).

    Args:
        registry: The ToolRegistry instance used to store discovered tools.
        user_tools_dir: The path to the directory containing user-defined tool modules.

    Raises:
        ImportError: when a file fails to import, breaks the ToolCategory contract, or defines
        @tool functions that belong to no category.
    """
    if not os.path.isdir(user_tools_dir):
        func.log(f"User tools directory not found: {user_tools_dir}", level="WARNING")
        return

    # Allow relative imports between user-defined tool files.
    if user_tools_dir not in sys.path:
        sys.path.insert(0, user_tools_dir)

    tool_count = 0
    try:
        for filename in sorted(os.listdir(user_tools_dir)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            module_name = filename[:-3]
            file_path = os.path.join(user_tools_dir, filename)
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not (spec and spec.loader):
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                categorized = set()
                for cls in _categories_in(module):
                    tools = registry.register_category(cls())
                    categorized.update(tools)
                    tool_count += len(tools)
                    func.log(f"Registered user tool category '{cls.name}' ({', '.join(tools)}) from {filename}", level="INFO")

                loose = _loose_tools(module, categorized)
                if loose:
                    raise ToolCategoryError(
                        f"@tool functions without a category: {', '.join(loose)}. Return them from the "
                        "get_category_tools() of a ToolCategory subclass (see ai.tools.category).")
            except Exception as e:
                func.log(f"Failed to load user tools from {filename}: {e}", level="ERROR")
                raise ImportError(f"Failed to load user tools from {filename}: {e}") from e
    finally:
        if user_tools_dir in sys.path:
            sys.path.remove(user_tools_dir)

    if tool_count > 0:
        func.log(f"Successfully loaded {tool_count} user tool(s).", level="INFO")
