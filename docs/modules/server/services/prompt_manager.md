## 1. Architectural Role
Provides a secure, file-system-based CRUD interface for managing Markdown-formatted prompt templates within a restricted root directory.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptError` | Class | Base exception for all prompt-related failures. |
| `PromptNotFoundError` | Class | Exception for missing prompt files. |
| `InvalidPathError` | Class | Exception for directory traversal or out-of-bounds path attempts. |
| `PromptAccessError` | Class | Exception for I/O or permission failures. |
| `PromptManager` | Class | Primary controller for prompt lifecycle and filesystem interaction. |
| `PromptManager.__init__` | Method | Sets the absolute `root_dir` and optional `logger`. |
| `PromptManager._log` | Method | Internal utility for safe, non-breaking execution of the `logger` callback. |
| `PromptManager._resolve_prompt_path` | Method | Validates and transforms relative strings into absolute `.md` paths while preventing directory traversal. |
| `PromptManager.list_prompts` | Method | Recursively scans the `root_dir` for `.md` files, returning metadata dictionaries. |
| `PromptManager.load_prompt` | Method | Reads and returns the string content of a specific `.md` file. |
| `PromptManager.save_prompt` | Method | Writes string content to a `.md` file, creating parent directories if necessary. |
| `PromptManager.read_prompt` | Method | Alias for `load_prompt`. |
| `PromptManager.create_prompt` | Method | Alias for `save_prompt`; returns success message. |
| `PromptManager.update_prompt` | Method | Alias for `save_prompt`; returns success message. |
| `PromptManager.delete_prompt` | Method | Removes a specific `.md` file from the filesystem. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `root_dir` and `logger`.
    2. Resolves `root_dir` to an absolute path using `.resolve()`.
    3. Stores the path and logger in the instance state.
- **Data Path**:
    - **Read Flow**: `prompt_path` (str) $\rightarrow$ `_resolve_prompt_path` (Path validation/suffixing) $\rightarrow$ `open()` $\rightarrow$ `content` (str).
    - **Write Flow**: `prompt_path` (str) + `content` (str) $\rightarrow$ `_resolve_prompt_path` $\rightarrow$ `mkdir(parents=True)` $\rightarrow$ `open(w)` $\rightarrow$ filesystem write.
    - **List Flow**: `sub_folder` (str) $\rightarrow$ `rglob("*.md")` $\rightarrow$ `relative_to(root_dir)` $\rightarrow$ `Dict` metadata collection $\rightarrow$ sorted `List[Dict]`.
- **Conditional Branching**:
    - **Path Security**: Checks if `".."` exists in the path string; checks if the resolved path's prefix matches `root_dir`.
    - **Existence Checks**: Verifies `exists()` and `is_file()` before reading or deleting.
    - **Error Handling**: Wraps I/O operations in `try/except` blocks to re-raise specific `PromptError` subtypes.

## 4. Resource Dependencies
- **Standard Libraries**: `pathlib.Path`, `typing` (`List`, `Dict`, `Optional`, `Any`, `Tuple`), `os`.
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `.md`: Forced file extension for all prompt operations.
    - `utf-8`: Default encoding for all file I/O.
- **Environment Lookups**: None.