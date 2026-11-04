## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Tool Loader** | [src/ai/tools/tool_loader.py](/src/ai/tools/tool_loader.py) |

The `tool_loader` component provides a dynamic mechanism for discovering and loading user-defined tools at runtime. It scans a specified directory for Python modules, imports them into the current process, and identifies specific functions intended to be used as tools based on a custom attribute marker.

This component serves as a bridge between the filesystem and the [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md), allowing for extensible agent capabilities without requiring modifications to the core codebase. It is a critical part of the tool management subsystem, enabling a plugin-like architecture for AI agent functions.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `load_and_register_user_tools(registry, user_tools_dir)` | Function | Scans `user_tools_dir` for `.py` files, imports them, and registers any callable objects possessing the `_is_tool` attribute into the provided `registry`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The loader iterates through files in the target directory, filtering for non-private Python files. It uses `importlib.util` to programmatically load modules. For each module, it inspects all attributes via `dir()`. If an attribute is a callable and has `_is_tool` set to `True`, it is registered with the `registry` using the function's `__name__` as the key.
- **Side Effects:** 
    - **Filesystem Access:** Reads directory contents and file metadata in the `user_tools_dir`.
    - **Python Path Mutation:** Temporarily inserts `user_tools_dir` into `sys.path` to facilitate relative imports within the loaded tools, and removes it upon completion.
    - **Global State Mutation:** Modifies `sys.modules` to ensure dynamically loaded modules are available for cross-importing.
    - **Logging:** Emits `INFO`, `WARNING`, and `ERROR` logs via the [functions](/AgentDocs/ai/functions.md) module.
- **Error Handling:** If a module fails to load, the component logs the error and raises an `ImportError` to prevent the system from running with an incomplete toolset.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `importlib.util`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md) (via `TYPE_CHECKING`)