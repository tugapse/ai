## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **tool_loader** | [src/ai/tools/tool_loader.py](/src/ai/tools/tool_loader.py) |

The `tool_loader` component provides dynamic discovery and registration of user-defined tools within the application. It allows developers to extend the agent's capabilities by simply placing Python files in a designated directory, facilitating a plugin-like architecture for tool expansion without requiring core code modifications.

This component acts as a bridge between the filesystem and the [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md). It scans a target directory, performs dynamic imports of Python modules, and inspects their contents for functions specifically marked as tools. It is a critical part of the tool management lifecycle, ensuring that external logic is correctly integrated into the agent's execution environment.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `load_and_register_user_tools(registry: "ToolRegistry", user_tools_dir: str)` | Function | Scans `user_tools_dir` for `.py` files, imports them, and registers any callable objects that possess the `_is_tool` attribute to the provided `registry`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function iterates through files in the specified directory, filtering for `.py` files that do not start with an underscore. It uses `importlib.util` to create module specs and load modules from file paths. To support cross-module imports within the user tools directory, it temporarily injects the directory into `sys.path` and adds the newly loaded modules to `sys.modules`. It then inspects every attribute of the loaded module, checking if the attribute is a callable and has a truthy `_is_tool` attribute.
- **Side Effects:** 
    - **Filesystem:** Reads the contents of the provided `user_tools_dir`.
    - **System State:** Modifies `sys.path` (temporarily) and `sys.modules` to facilitate dynamic loading.
    - **Logging:** Emits logs via [ai.functions](/AgentDocs/ai/functions.md) at `INFO`, `WARNING`, and `ERROR` levels.
- **Error Handling:** If a module fails to load, the function logs the error and raises an `ImportError` to prevent the system from running with a partially loaded or corrupted toolset.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `importlib.util`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.tools.tool_registry.ToolRegistry](/AgentDocs/ai/tools/tool_registry.md) (via `TYPE_CHECKING`)