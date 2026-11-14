## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| tool_loader | ai/tools/tool_loader.md |

This component is responsible for dynamically discovering and loading external functions—referred to as "tools"—from a specified directory of user-defined Python modules. Its primary responsibility is to scan the provided directory, import each `.py` file as a module, and introspect those modules to find any callable functions explicitly marked with the `_is_tool` attribute.

It functions as a critical discovery and integration service within the application's architecture. It sits between the filesystem layer and the core tool execution logic, populating the central [ToolRegistry](/ai/tools/tool_registry.md) with available capabilities so that the main application logic can subsequently invoke them.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| load_and_register_user_tools | Function | Scans a directory for Python files, imports them, and registers any functions marked with the @_is_tool attribute. Takes the `ToolRegistry` instance and the `user_tools_dir` path as arguments. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function iterates over files in the `user_tools_dir`. For each Python file, it uses `importlib.util` to load the module dynamically. It then iterates through all attributes of the loaded module, checking if the attribute is callable and possesses the `_is_tool` flag set to `True`. If both conditions are met, the function is registered with the provided `ToolRegistry`. The directory is temporarily added to `sys.path` to facilitate potential cross-imports between user tools.

- **Side Effects:** Reads the filesystem (`os.listdir`, `os.path.isdir`), modifies the global `sys.path`, and executes external code modules, which constitutes filesystem interaction and state mutation.

- **Error Handling:** It catches general `Exception` during module loading, logs the failure, and re-raises it as an `ImportError`, ensuring that loading failures are surfaced to the caller.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `importlib.util`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ToolRegistry](/ai/tools/tool_registry.md)