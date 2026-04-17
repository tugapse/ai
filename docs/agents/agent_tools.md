## 1. Architectural Role
Provides a suite of filesystem, shell execution, and system notification tools designed for an AI agent to interact with the local project environment via a restricted, path-sanitized interface.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `send_notification` | Func | Triggers system desktop notifications via `notify-send`. |
| `execute_command` | Func | Runs shell commands with `@ROOT` path resolution and timeout controls. |
| `read_dir` | Func | Recursively maps directory structures (files/folders) up to a specified depth. |
| `read_file` | Func | Extracts UTF-8 text content from one or multiple specified files. |
| `write_file` | Func | Creates or overwrites files, ensuring parent directories exist. |
| `smart_search` | Func | Performs regex/literal searches across filenames and file contents with pagination. |
| `patch_file` | Func | Performs a surgical string replacement in a file if a unique match is found. |
| `AVAILABLE_TOOLS` | Dict | Registry mapping tool names to their respective function implementations. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Sets `PROJECT_ROOT` to the current working directory.
    - Defines internal helper functions (`_resolve_path`, `_sanitize_output_path`, `_ensure_list`) for path validation and input normalization.
- **Data Path**: 
    - **Input**: Tool functions receive `**kwargs` containing paths, patterns, or content.
    - **Processing**: 
        1. Paths are passed through `_resolve_path` to convert `@ROOT` tokens to absolute paths and enforce project boundary constraints.
        2. Logic is executed (e.g., `subprocess.run` for commands, `os.walk` for search, `open()` for file I/O).
        3. Output paths are passed through `_sanitize_output_path` to convert absolute paths back to `@ROOT` format.
    - **Output**: Returns a dictionary containing a `status` ("SUCCESS" or "FAILED") and the resulting data or error message.
- **Conditional Branching**:
    - **Path Validation**: If a resolved path is outside `PROJECT_ROOT`, a `PermissionError` is raised.
    - **Patch Guardrail**: In `patch_file`, if the `search` block is missing or appears more than once, the operation fails to prevent accidental corruption.
    - **Search Pagination**: `smart_search` calculates `total_pages` and slices results based on the `page` argument.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `shutil`, `subprocess`, `requests`, `json`, `difflib`, `re`, `math`, `typing`
- **Internal Modules**: `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `PAGE_SIZE = 50` (used in `smart_search`).
    - `default_excludes = [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]` (used in `smart_search`).
    - Default notification timeout: `5000`ms.
    - Default command timeout: `60`s.
- **Environment Lookups**: None.