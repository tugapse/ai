import os
import sys
import importlib.util
from typing import TYPE_CHECKING
import ai.functions as func

if TYPE_CHECKING:
    from .tool_registry import ToolRegistry

def load_and_register_user_tools(registry: "ToolRegistry", user_tools_dir: str):
    """
    Scans a directory for Python files, imports them, and registers any functions
    marked with the @_is_tool attribute.
    """
    if not os.path.isdir(user_tools_dir):
        func.log(f"User tools directory not found: {user_tools_dir}", level="WARNING")
        return

    # Add the user tools directory to the Python path to allow for relative imports
    # between user-defined tools.
    if user_tools_dir not in sys.path:
        sys.path.insert(0, user_tools_dir)

    tool_count = 0
    for filename in os.listdir(user_tools_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            file_path = os.path.join(user_tools_dir, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Add module to sys.modules to handle potential cross-imports in tools
                    sys.modules[module_name] = module 
                    spec.loader.exec_module(module)
                    
                    for attr_name in dir(module):
                        func_ref = getattr(module, attr_name)
                        if callable(func_ref) and hasattr(func_ref, "_is_tool") and func_ref._is_tool:
                            tool_name = func_ref.__name__
                            registry.register_tool(tool_name, func_ref)
                            func.log(f"Dynamically registered tool: '{tool_name}' from {filename}", level="INFO")
                            tool_count += 1

            except Exception as e:
                func.log(f"Failed to load user tool from {filename}: {e}", level="ERROR")
                raise ImportError(f"Failed to load user tool from {filename}: {e}") from e
    
    if tool_count > 0:
        func.log(f"Successfully loaded {tool_count} user tool(s).", level="INFO")

    # Clean up the path modification if desired, although it's often fine to leave it
    # for the duration of the process.
    if user_tools_dir in sys.path:
        sys.path.remove(user_tools_dir)