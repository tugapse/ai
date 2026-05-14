## 1. Architectural Role
Provides a set of sandboxed, filesystem-aware, and shell-capable utility functions decorated for automatic discovery by an agentic system to facilitate environment interaction.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `tool` | Decorator | Marks functions with `_is_tool = True` for system registration. |
| `_resolve_path` | Func | Normalizes `@ROOT` tokens, enforces type-safety, and validates project boundary constraints. |
| `_sanitize_output_path` | Func | Converts absolute system paths back into `@ROOT` relative format for LLM consumption. |
| `ensure_list` | Func | Casts various input types (str, list, JSON-string) into a standardized `List[str]`. |
| `execute_command` | Func | Executes shell commands via `subprocess` with timeout and directory scoping. |
| `read_dir` | Func | Recursively traverses directories to return a structured JSON-like map of files and folders. |
| `read_file` | Func | Retrieves UTF-8 text content from one or multiple specified file paths. |
| `write_file` | Func | Creates or overwrites files and automatically generates missing parent directories. |
| `smart_search` | Func | Performs keyword/regex searches across filenames and file contents with pagination. |
| `patch_file` | Func | Performs surgical string replacement within a file using exact block matching. |
| `AVAILABLE_TOOLS` | Dict | Registry mapping tool names to their respective function implementations. |

## 3. Execution Logic & Flow
- **Initialization**: Sets `PROJECT_ROOT` via `os.getcwd()` upon module import.
- **Data Path**: 
    1. **Input**: Receives `**kwargs` containing `intent`, `path`/`paths`, and tool-specific parameters.
    2. **Processing**: 
        - Path resolution via `_resolve_path` (Token replacement $\rightarrow$ Absolute path conversion $\rightarrow$ Boundary check).
        - Type normalization via `ensure_list`.
        - Core logic execution (e.g., `subprocess.run`, `os.walk`, `open().read()`).
    3. **Output**: Returns a `Dict[str, Any]` containing a `status` ("SUCCESS" or "FAILED"), payload (results/files/content), and optional `error` or `diff_summary`.
- **Conditional Branching**:
    - **Security Check**: `_resolve_path` raises `PermissionError` if the target path is outside `PROJECT_ROOT`.
    - **Error Aggregation**: `read_dir` and `read_file` track `had_errors` to return partial results or a consolidated error status.
    - **Search Logic**: `smart_search` toggles between regex compilation and literal string matching.
    - **Patch Uniqueness**: `patch_file` validates that the `search` block is present and unique before applying changes.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `shutil`, `subprocess`, `requests`, `json`, `difflib`, `typing`, `re`, `math`.
- **Internal Modules**: `functions` (as `func`).

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `PAGE_SIZE = 50` (in `smart_search`).
    - `default_excludes` (in `smart_search`).
    - `timeout = 60` (default in `execute_command`).
- **Environment Lookups**: `os.getcwd()` (used to define `PROJECT_ROOT`).