## 1. Architectural Role
The `PromptManager` serves as the specialized filesystem abstraction layer within [modules/server/services/prompt_manager.md](modules/server/services/prompt_manager.md), responsible for the secure lifecycle management of Markdown-based prompt templates. It enforces strict directory traversal prevention to ensure all I/O operations remain encapsulated within a designated root directory, providing a standardized interface for listing, loading, saving, and deleting prompt assets used by the broader server architecture.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `.md` (Default: `suffix`)  Enforced file extension for all prompt operations.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptError` | Class | Base exception for all prompt-related domain errors. |
| `PromptNotFoundError` | Class | Exception raised when a file is missing from the filesystem. |
| `InvalidPathError` | Class | Exception raised when a path violates security constraints (traversal). |
| `PromptAccessError` | Class | Exception raised for low-level OS/IO failures. |
| `PromptManager` | Class | Primary orchestrator for prompt filesystem operations. |
| `_resolve_prompt_path` | Method | Internal security validator that resolves and sanitizes relative paths. |
| `list_prompts` | Method | Scans the root directory (or sub-folders) for `.md` files and returns metadata. |
| `load_prompt` | Method | Reads and returns the string content of a specific prompt file. |
| `save_prompt` | Method | Writes string content to a file, creating parent directories if necessary. |
| `read_prompt` | Method | Alias for `load_prompt`. |
| `create_prompt` | Method | Alias for `save_prompt`; returns success message. |
| `update_prompt` | Method | Alias for `save_prompt`; returns success message. |
| `delete_prompt` | Method | Removes a prompt file from the filesystem. |

## 4. Execution Logic & Flow
- **Initialization**: Sets the `root_dir` as an absolute, resolved `Path` and assigns an optional logger.
- **Data Path**:
    - **Input**: A relative string path (e.g., `"templates/persona"`).
    - **Processing**: 
        1. Check for `..` components to block traversal.
        2. Append `.md` suffix.
        3. Resolve to absolute path.
        4. Verify the resolved path starts with the `root_dir` prefix.
    - **Output**: A validated absolute `Path` object or a `PromptError` exception.
- **Conditional Branching**:
    - **Path Validation**: If `..` is detected in path components, `InvalidPathError` is raised.
    - **Root Escape Check**: If `resolved.startswith(root_dir)` is false, `InvalidPathError` is raised.
    - **File Existence**: If `path.exists()` is false during load/delete, `PromptNotFoundError` is raised.
    - **Logger Check**: If `self.logger` is not `callable`, logging is skipped.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib`, `typing`, `os`
- **Internal Modules**: 
    - No internal module imports identified (logic is self-contained within the file).
- **External Packages**: None identified.