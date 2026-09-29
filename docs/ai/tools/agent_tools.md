## 1. Architectural Role
| :--- | :--- |
| Name | Agent Tools |
| Source file | agent_tools.py |

The **agent_tools** component serves as the primary interface between the AI agent's reasoning engine and the host operating system's file system and shell environment. It provides a controlled, sandboxed set of capabilities that allow an LLM to interact with the codebase, execute commands, and manipulate files while maintaining strict security boundaries via project-root enforcement.

**Functional Mission**
The primary responsibility of **agent_tools** is to provide a high-level, structured API for file system operations and command execution. It solves the problem of safe, predictable tool-calling by abstracting raw OS operations into "intent-aware" functions that handle path normalization, security validation, and error reporting in a format suitable for LLM consumption.

**System Context & Integration**
This component acts as the "hands" of the agent. It is designed to be discovered and registered by the system, likely via [tool_loader.md](/docs/ai/tools/tool_loader.md) and [tool_registry.md](/docs/ai/tools/tool_registry.md). When an agent decides to perform an action, it invokes these functions, which then interact with the local environment. The output of these tools (stdout, file contents, or directory structures) is fed back into the agent's context, facilitating a closed-loop interaction cycle.

- **INTERNAL REFERENCES**: The tools are intended to be utilized by [agent.md](/docs/ai/agents/agent.md) to perform environmental manipulations.

## 2. Environment & Configuration
**Environment Lookups:**
- `PROJECT_ROOT` (via `os.getcwd()`)  Determines the absolute base directory for all path resolutions and security boundary checks.

**Hardcoded Constants:**
- `PAGE_SIZE` (Default: `50`)  Limits the number of search results returned per page in `smart_search` to prevent context window overflow.
- `default_excludes` (Default: `[".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]`)  Standard directories ignored during file system traversal.
- `timeout` (Default: `180`)  Maximum execution time for shell commands in `execute_command`.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `tool` | Decorator | Marks functions for automatic discovery and registration by the tool loader. |
| `execute_command` | Function | Runs shell commands within a specified directory, handling `@ROOT` token replacement and timeout management. |
| `read_dir` | Function | Recursively explores directories and returns a structured mapping of files and folders. |
| `read_file` | Function | Retrieves UTF-8 text content from one or multiple specified file paths. |
| `write_file` | Function | Creates or overwrites files, automatically handling parent directory creation. |
| `smart_search` | Function | Performs keyword or regex searches across filenames and file contents with pagination. |
| `patch_file` | Function | Performs surgical text replacement within a file using exact string matching to prevent accidental corruption. |

## 4. Execution Logic & Flow
- **Initialization**: The module establishes `PROJECT_ROOT` upon import using the current working directory.
- **Data Path**:
    1. **Input**: Receives keyword arguments (`kwargs`) containing `intent`, `path`/`paths`, `command`, `content`, or `pattern`.
    2. **Processing**: 
        - Paths are passed through `_resolve_path` to convert `@ROOT` tokens to absolute paths and validate they reside within `PROJECT_ROOT`.
        - Inputs are sanitized via `ensure_list` to handle various LLM output formats (strings, lists, or JSON-like strings).
        - Operations (read/write/execute) are performed using standard Python `os`, `subprocess`, or `open` modules.
    3. **Output**: Returns a dictionary containing a `status` ("SUCCESS" or "FAILED"), the requested data (content, results, or diffs), and error messages if applicable.
- **Conditional Branching**:
    - **Security Check**: `_resolve_path` raises a `PermissionError` if a requested path attempts to escape the `PROJECT_ROOT`.
    - **Uniqueness Check**: `patch_file` fails if the `search` block is not found or if it is not unique within the file, preventing ambiguous edits.
    - **Error Aggregation**: `read_file` and `read_dir` track `had_errors` to return a partial success/failure summary if some paths in a list are invalid.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `subprocess`, `json`, `difflib`, `typing`, `re`, `math`
- **Internal Modules**: 
    - No direct internal module imports found in the provided source.
- **External Packages**: None identified.