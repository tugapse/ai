## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| base | /ai/tools/base.md |

This component provides the foundational utilities necessary for defining, discovering, and safely utilizing agent tools within the application. It establishes the core mechanisms, such as the `@tool` decorator, which marks functions as discoverable agents, and provides essential path resolution helpers that enforce security boundaries around file operations.

Architecturally, this module serves as a crucial utility layer situated between the tool definitions (which reside in various `ai.modules.tools_*` modules) and the core execution engine. It acts as the centralized authority for path management, ensuring that tools interact with the filesystem in a controlled and secure manner by referencing the project root via `PROJECT_ROOT` and providing methods like [resolve_path](/ai/tools/base.md) for safe I/O.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `get_project_root()` | Function | Returns the absolute path of the project root as currently defined by `PROJECT_ROOT`. |
| `tool(func)` | Decorator | Marks a function as an agent tool, adding the `_is_tool` attribute for automatic discovery. |
| `collect_tools(*sources)` | Function | Scans provided sources (modules, callables, or iterables) to find and return a dictionary of all functions marked with `@tool`. |
| `resolve_path(params)` | Function | Resolves a path specified in parameters ('path', 'filepath', or 'location') into an absolute, normalized path within the project root, raising `PermissionError` if the path escapes the boundaries. |
| `sanitize_output_path(full_path)` | Function | Converts an absolute system path back into the project-relative `@ROOT` format, or returns "EXTERNAL_PATH" if the path is outside the project. |
| `ensure_list(input_val)` | Function | Robustly converts various inputs (string, list, JSON string) into a standardized list of strings. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The module centers around path security. `resolve_path` first extracts a raw path, normalizes it against the project root, and then performs a critical security check using `os.path.realpath` and `os.path.commonpath` to verify that the resolved path remains strictly within the designated project directory. `collect_tools` iterates through sources, checking for the presence of the `_is_tool` marker.
- **Side Effects:** Reads/writes to the filesystem (via `os.getcwd()` and `os.path.realpath`/`os.path.abspath` in path helpers). It mutates the global `PROJECT_ROOT` variable if reassigned externally.
- **Error Handling:** `resolve_path` explicitly raises `PermissionError` if the resolved path attempts to access outside the project boundaries. `sanitize_output_path` uses a general `try...except` block to handle potential filesystem errors during path conversion, falling back to "@ROOT/unknown".

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `os`, `types`, `typing`
- **Internal:** None