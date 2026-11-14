## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| PromptManager | /ai/modules/server/services/prompt_manager.md |

This component is responsible for the entire lifecycle management of prompt assets within the application. It provides robust mechanisms to locate, read, write, update, and delete prompt files, ensuring all operations are confined strictly within a designated root directory. Its primary focus is providing a safe and predictable interface for interacting with stored prompt configurations.

This service acts as a crucial utility layer within the server architecture, mediating between the core application logic and the persistent storage of prompts. It relies on strict path validation, particularly within the `_resolve_prompt_path` method, to prevent security vulnerabilities like directory traversal, thereby enforcing architectural boundaries between prompt storage and the rest of the system.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| PromptManager | Class | Manages the lifecycle of prompt files within a root directory, enforcing path security. |
| list_prompts | Method | Lists all prompts (as files) under the root directory, optionally filtered by a sub-folder. |
| load_prompt | Method | Loads the full content of a single prompt file identified by its path string. |
| save_prompt | Method | Saves or overwrites a prompt file with the provided string content. |
| read_prompt | Method | Alias for `load_prompt`, used for backward compatibility. |
| create_prompt | Method | Alias for `save_prompt`, used for backward compatibility to create a new prompt. |
| update_prompt | Method | Alias for `save_prompt`, used for backward compatibility to overwrite an existing prompt. |
| delete_prompt | Method | Deletes a specific prompt file identified by its path string. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager relies on `pathlib.Path` objects for reliable filesystem operations. Path resolution is critical; `_resolve_prompt_path` ensures that any requested path, after being joined with the `root_dir`, resolves back into a path that starts with the `root_dir` itself, thus preventing external file access. Listing uses `rglob` for recursive searching.
- **Side Effects:** Reads from and writes to the filesystem (disk I/O) when calling `load_prompt`, `save_prompt`, and `delete_prompt`. It also interacts with the provided `logger` if initialized.
- **Error Handling:** It defines specific exceptions (`PromptNotFoundError`, `InvalidPathError`, `PromptAccessError`) to categorize failures. `InvalidPathError` is specifically raised when path traversal attempts are detected during resolution.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `typing`, `os`.
- **Internal:** None.