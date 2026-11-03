## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **PromptManager** | [src/ai/modules/server/services/prompt_manager.py](/AgentDocs/ai/modules/server/services/prompt_manager.md) |

The `PromptManager` is a specialized service designed to manage the lifecycle of prompt templates stored as Markdown files. It provides a structured interface for listing, reading, creating, updating, and deleting prompts while ensuring that all file operations remain contained within a designated root directory.

This component serves as a critical backend service within the server module, likely utilized by [src/ai/modules/server/routers/prompts.py](/AgentDocs/ai/modules/server/routers/prompts.md) to expose prompt management capabilities via API endpoints. By enforcing strict path validation, it prevents directory traversal attacks and ensures the integrity of the prompt storage system.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `PromptError` | Exception | Base exception for all prompt-related errors. |
| `PromptNotFoundError` | Exception | Raised when a requested prompt file does not exist. |
| `InvalidPathError` | Exception | Raised when a provided path attempts to escape the root directory. |
| `PromptAccessError` | Exception | Raised on generic I/O or filesystem access errors. |
| `PromptManager` | Class | The primary controller for prompt lifecycle management. |
| `PromptManager.__init__(root_dir, logger)` | Constructor | Initializes the manager with a resolved `root_dir` and an optional logger. |
| `list_prompts(sub_folder=None)` | Method | Returns a list of dictionaries containing metadata (`name`, `path`, `last_modified`) for all `.md` files in the root or a sub-folder. |
| `load_prompt(prompt_path)` | Method | Loads and returns the string content of a prompt file. |
| `save_prompt(prompt_path, content)` | Method | Writes or overwrites a prompt file with the provided string content. |
| `read_prompt(prompt_path)` | Method | Alias for `load_prompt`. |
| `create_prompt(prompt_path, content)` | Method | Alias for `save_prompt`; returns a confirmation dictionary. |
| `update_prompt(prompt_path, content)` | Method | Alias for `save_prompt`; returns a confirmation dictionary. |
| `delete_prompt(prompt_path)` | Method | Deletes the specified prompt file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses `pathlib` for all filesystem operations. It implements a security layer in `_resolve_prompt_path` that checks for the presence of `..` in path segments and verifies that the resolved absolute path starts with the `root_dir` prefix. This prevents unauthorized access to files outside the prompt repository.
- **Side Effects:** 
    - **Filesystem I/O:** Performs extensive read, write, and delete operations on the local filesystem.
    - **Directory Creation:** `save_prompt` will automatically create parent directories if they do not exist.
    - **Logging:** If a callable `logger` is provided during initialization, the class will emit log messages during path validation failures or I/O errors.
- **Error Handling:** The class uses a hierarchy of custom exceptions (`PromptError` $\rightarrow$ `PromptNotFoundError`, `InvalidPathError`, `PromptAccessError`) to allow callers to distinguish between missing files, security violations, and general system errors.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `typing`, `os`.
- **Internal:** No internal module imports detected.