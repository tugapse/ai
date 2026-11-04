## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **PromptManager** | [src/ai/modules/server/services/prompt_manager.py](/src/ai/modules/server/services/prompt_manager.py) |

The `PromptManager` is responsible for the lifecycle management of Markdown-based prompt files. It provides a structured interface for listing, loading, creating, updating, and deleting prompts within a strictly controlled filesystem directory.

This component serves as a backend service within the server module, likely utilized by [src/ai/modules/server/routers/prompts.py](/src/ai/modules/server/routers/prompts.md) to expose prompt management capabilities via an API. Its primary purpose is to ensure that prompt operations are safe, preventing directory traversal attacks by validating all requested paths against a designated root directory.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `PromptError` | Exception | Base exception for all prompt-related errors. |
| `PromptNotFoundError` | Exception | Raised when a requested prompt file does not exist. |
| `InvalidPathError` | Exception | Raised when a provided path attempts to escape the root prompt directory. |
| `PromptAccessError` | Exception | Raised on generic IO or access errors during prompt operations. |
| `PromptManager` | Class | The primary service for managing prompt files. |
| `PromptManager.__init__(root_dir, logger)` | Constructor | Initializes the manager with a resolved `root_dir` and an optional callable `logger`. |
| `list_prompts(sub_folder=None)` | Method | Returns a list of dictionaries containing `name`, `path`, and `last_modified` for all `.md` files in the root or a sub-folder. |
| `load_prompt(prompt_path)` | Method | Reads and returns the string content of a prompt file. |
| `save_prompt(prompt_path, content)` | Method | Writes string content to a prompt file, creating parent directories if necessary. |
| `read_prompt(prompt_path)` | Method | Alias for `load_prompt`. |
| `create_prompt(prompt_path, content)` | Method | Alias for `save_prompt`; returns a success message dictionary. |
| `update_prompt(prompt_path, content)` | Method | Alias for `save_prompt`; returns a success message dictionary. |
| `delete_prompt(prompt_path)` | Method | Deletes the specified prompt file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses `pathlib.Path` for all filesystem operations. A critical internal method, `_resolve_prompt_path`, performs security validation by checking for `..` components and ensuring the resolved absolute path starts with the `root_dir` string. This prevents unauthorized access to files outside the prompt repository.
- **Side Effects:** 
    - **Filesystem IO:** Performs extensive read, write, and delete operations on the local filesystem.
    - **Directory Creation:** `save_prompt` will automatically create missing parent directories using `mkdir(parents=True)`.
    - **Logging:** If a callable `logger` is provided during initialization, the class will attempt to log operational events (e.g., found prompts, invalid path attempts).
- **Error Handling:** The component uses a hierarchy of custom exceptions (`PromptError` $\rightarrow$ `PromptNotFoundError`, `InvalidPathError`, `PromptAccessError`) to allow callers to distinguish between missing files, security violations, and general IO failures.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `typing`, `os`.
- **Internal:** No internal module imports detected in this file.