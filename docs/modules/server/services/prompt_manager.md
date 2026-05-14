## 1. Architectural Role

**Functional Mission**
The **PromptManager** serves as the specialized filesystem abstraction layer responsible for the lifecycle management of Markdown-based prompt templates. Its core mission is to provide a secure, structured interface for reading, writing, listing, and deleting prompt files while enforcing strict directory traversal protections to ensure that prompt operations remain confined to a designated root directory.

**System Context & Integration**
This component acts as a critical data provider for the server-side orchestration layer. It facilitates the transition of raw text templates from persistent storage into the active execution flow, likely feeding into modules such as [Brain Hub](/docs/modules/server/brain_hub.md) or [Template Injection](/docs/core/template_injection.md) for dynamic content generation. By centralizing prompt I/O, it ensures that downstream LLM services interact with a consistent and validated set of instructions.

## 2. Environment & Configuration

**Environment Lookups:**
- `root_dir` (via `__init__`)  Defines the absolute base directory for all prompt storage operations.

**Hardcoded Constants:**
- `.md` (Default: `.md`)  Hardcoded file extension enforced for all prompt resolution and discovery.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptError` | Class | Base exception for all prompt-related failures. |
| `PromptNotFoundError` | Class | Exception raised when a specific prompt file is missing. |
| `InvalidPathError` | Class | Exception raised when a path attempts to escape the `root_dir`. |
| `PromptAccessError` | Class | Exception raised for OS-level I/O or permission failures. |
| `PromptManager` | Class | Primary controller for prompt filesystem operations. |
| `_log` | Method | Internal utility for handling optional logger callbacks. |
| `_resolve_prompt_path` | Method | Validates and converts relative paths to absolute, sandboxed `.md` paths. |
| `list_prompts` | Method | Scans the `root_dir` (or subfolder) for `.md` files and returns metadata. |
| `load_prompt` | Method | Reads and returns the string content of a prompt file. |
| `save_prompt` | Method | Writes string content to a file, creating parent directories if needed. |
| `read_prompt` | Method | Alias for `load_prompt`. |
| `create_prompt` | Method | Alias for `save_prompt`; returns a success message. |
| `update_prompt` | Method | Alias for `save_prompt`; returns a success message. |
| `delete_prompt` | Method | Removes a prompt file from the filesystem. |

## 4. Execution Logic & Flow

- **Initialization**: The manager is instantiated with a `root_dir` (Path object) and an optional `logger`. The `root_dir` is immediately resolved to its absolute path to prevent ambiguity.
- **Data Path**:
    - **Input**: A relative string path (e.g., `"templates/system_prompt"`).
    - **Processing**: 
        1. Path is checked for `".."` components.
        2. `.md` suffix is appended.
        3. Path is resolved to an absolute location.
        4. The resolved path is checked to ensure it starts with the `root_dir` string.
    - **Output**: An absolute `Path` object pointing to a valid file, or an exception.
- **Conditional Branching**:
    - **Path Validation**: If `".."` is detected or the resolved path is outside `root_dir`, `InvalidPathError` is raised.
    - **File Existence**: In `load_prompt` and `delete_prompt`, if the resolved path does not exist, `PromptNotFoundError` is raised.
    - **I/O Errors**: Any `OSError` or permission issues during file operations are caught and re-raised as `PromptAccessError`.

## 5. Resource Dependencies

- **Standard Libraries**: `pathlib`, `typing`, `os`
- **Internal Modules**: 
    - No direct internal module imports found in the provided source.
- **External Packages**: None identified.