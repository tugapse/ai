"""
Shared building blocks for agent tools.

Tool implementations live in app modules (``ai.modules.tools_*``); this module
holds what they share: the ``@tool`` marker, the project root that ``@ROOT``
refers to, and path helpers that keep tools inside the project.
"""

import json
import os
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List

# Directory that '@ROOT' refers to. Read through get_project_root() at call time so
# tests (and embedders) can repoint it by assigning ai.tools.base.PROJECT_ROOT.
PROJECT_ROOT = os.getcwd()


def get_project_root() -> str:
    return PROJECT_ROOT


def tool(func: Callable) -> Callable:
    """
    Decorator to mark a function as an agent tool.
    This allows the system to discover and register it automatically.
    """
    func._is_tool = True
    return func


def collect_tools(*sources: Any) -> Dict[str, Callable]:
    """
    Collects @tool functions from modules, iterables of functions, or functions.

    Returns:
        {tool_name: function}, in discovery order.
    """
    found: Dict[str, Callable] = {}
    for source in sources:
        if isinstance(source, ModuleType):
            candidates: Iterable[Any] = (getattr(source, name) for name in dir(source))
        elif callable(source):
            candidates = [source]
        else:
            candidates = source
        for candidate in candidates:
            if callable(candidate) and getattr(candidate, "_is_tool", False):
                found[candidate.__name__] = candidate
    return found


# --- PATH HELPERS ---
def resolve_path(params: Dict[str, Any]) -> str:
    """
    Resolves a path with strict type-safety to prevent 'normalize' crashes.

    Args:
        params: A dictionary containing path keys ('path', 'filepath', or 'location').

    Returns:
        str: The absolute, normalized path within the project root.

    Raises:
        PermissionError: If the resolved path attempts to access outside the project boundaries.
    """
    # 1. Extraction with fallback
    raw_path = params.get("path") or params.get("filepath") or params.get("location") or "."

    # 2. Resilience: If the LLM sent a list or a nested dictionary by mistake
    if isinstance(raw_path, list) and len(raw_path) > 0:
        raw_path = raw_path[0]
    elif isinstance(raw_path, dict):
        # Extract the first string value found in the dict, or default to root
        raw_path = next((v for v in raw_path.values() if isinstance(v, str)), ".")

    # 3. Type Enforcement: Ensure we have a string before calling .replace() or os.path
    if not isinstance(raw_path, str):
        raw_path = str(raw_path) if raw_path is not None else "."

    # 4. Normalization
    normalized = raw_path.replace("@ROOT/", "").replace("@ROOT", ".")
    absolute_target = os.path.abspath(os.path.join(get_project_root(), normalized))

    # 5. Security Check
    if not absolute_target.startswith(os.path.abspath(get_project_root())):
        raise PermissionError(f"Access denied: {raw_path} is outside project boundaries.")
    
    return absolute_target

def sanitize_output_path(full_path: str) -> str:
    """
    Converts absolute system paths back into the @ROOT format for LLM consumption.

    Args:
        full_path: The absolute path obtained from the filesystem.

    Returns:
        str: The path represented in the @ROOT format, or "EXTERNAL_PATH" if outside the project.
    """
    try:
        full_path = os.path.abspath(full_path)
        root = get_project_root()
        if full_path.startswith(root):
            relative = os.path.relpath(full_path, root)
            return (
                "@ROOT" if relative == "." else f"@ROOT/{relative.replace(os.sep, '/')}"
            )
        return "EXTERNAL_PATH"
    except:
        return "@ROOT/unknown"

def ensure_list(input_val: Any) -> List[str]:
    """
    Helper to ensure input is a list of strings, handling various input formats (str, list, JSON string).

    Args:
        input_val: The value to check and convert.

    Returns:
        List[str]: A list containing the string representations of the input.
    """
    if isinstance(input_val, list):
        return input_val
    if isinstance(input_val, str):
        cleaned = input_val.strip()
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                return json.loads(cleaned)
            except:
                return [cleaned]
        return [cleaned]
    return []


# Backwards-compatible private names
_resolve_path = resolve_path
_sanitize_output_path = sanitize_output_path
