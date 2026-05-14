## 1. Architectural Role
Acts as the primary capability layer for the autonomous agent, providing a suite of sandboxed filesystem and shell operations. It serves as the bridge between high-level LLM intent and low-level OS execution, implementing strict security boundaries via `@ROOT` path resolution to prevent directory traversal attacks. These tools are intended to be discovered and utilized by [agents/agent.md](agents/agent.md) through the orchestration mechanisms defined in [tools/tool_loader.md](tools/tool_loader.md) and [tools/tool_registry.md](tools/tool_registry.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `PROJECT_ROOT` (via `os.getcwd()`)  Establishes the absolute base directory for all sandboxed operations.

**Hardcoded Constants:**
- `PAGE_SIZE` (Default: `50`)  Limits search result chunks to prevent LLM context overflow.
- `default_excludes` (Default: `[".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]`)  Standard directories ignored during recursive searches.
- `timeout` (Default: `60`)  Maximum duration for shell command execution.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `tool` | Decorator | Marks functions with `_is_tool = True` for automated registry discovery. |
| `_resolve_path` | Internal Func | Sanitizes and validates input paths against `PROJECT_ROOT` to ensure security. |
| `_sanitize_output_path` | Internal Func | Converts absolute system paths into the `@ROOT` abstraction for agent readability. |
| `ensure_list` | Internal Func | Normalizes diverse input types (str, list, JSON-string) into a standard list. |
| `execute_command` | Function | Runs shell commands via `subprocess` within the defined project environment. |
| `read_dir` | Function | Recursively maps directory structures (files/folders) up to a specified depth. |
| `read_file` | Function | Retrieves UTF-8 text content from specified file paths. |
| `write_file` | Function | Creates or overwrites files and automatically generates missing parent directories. |
| `smart_search` | Function | Performs dual-mode searching (regex/literal) across filenames and file contents. |
| `patch_file` | Function | Performs surgical text replacement using unique block matching and diff generation. |
| `AVAILABLE_TOOLS` | Dictionary | The registry mapping tool names to their executable function references. |

## 4. Execution Logic & Flow
- **Initialization**: Sets `PROJECT_ROOT` based on the current working directory.
- **Data Path**: 
    - **Input**: Agent provides a dictionary of parameters (`kwargs`) containing `intent`, `path`, `command`, `content`, etc.
    - **Processing**: 
        1. Paths are passed through `_resolve_path` to enforce `@ROOT` boundaries.
        2. `ensure_list` standardizes path arrays.
        3. Logic executes (e.g., `subprocess.run` for commands, `os.walk` for search, or `open().write()` for files).
        4. Output is processed via `_sanitize_output_path` to mask system-specific paths.
    - **Output**: Returns a status-wrapped dictionary (`status`, `results`/`files`/`diff_summary`, and optional `error`).
- **Conditional Branching**:
    - **Security Gate**: `_resolve_path` raises `PermissionError` if a resolved path sits outside `PROJECT_ROOT`.
    - **Error Handling**: Most tools wrap execution in `try/except` blocks, returning a `FAILED` status rather than crashing the process.
    - **Search Logic**: `smart_search` switches between regex matching and literal substring matching depending on pattern validity.
    - **Uniqueness Check**: `patch_file` aborts if the `search` block is not unique within the target file.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `shutil`, `subprocess`, `requests`, `json`, `difflib`, `typing`, `re`, `math`
- **Internal Modules**: 
    - [functions](functions.md)
- **External Packages**: None identified.