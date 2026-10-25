## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | PromptManager |
| Source file | prompt_manager.py |

The **PromptManager** serves as the centralized filesystem abstraction layer for managing Markdown-based prompt templates. It provides a secure, controlled interface for the lifecycle of prompt assets, including discovery, retrieval, persistence, and deletion, while enforcing strict directory traversal protections to ensure system integrity.

**Functional Mission**
The primary responsibility of the **PromptManager** is to manage the storage and retrieval of prompt files within a designated root directory. It solves the problem of unstructured prompt management by enforcing a standardized `.md` file extension, providing a structured API for CRUD operations, and implementing security measures to prevent unauthorized file access via directory traversal attacks.

**System Context & Integration**
This component acts as a critical data provider for the server-side architecture. It is primarily utilized by routing layers, such as [prompts](/docs/ai/modules/server/routers/prompts.md), to expose prompt management capabilities via API endpoints. By abstracting the filesystem, it ensures that downstream serviceswhich require specific prompt content to drive LLM interactionsreceive validated and sanitized data. It functions as a specialized service within the server module, bridging the gap between raw disk storage and the application's logical prompt requirements.

- **INTERNAL REFERENCES**: [prompts](/docs/ai/modules/server/routers/prompts.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `PromptError` | Class | Base exception for all prompt-related failures. |
| `PromptNotFoundError` | Class | Exception raised when a requested prompt file is missing. |
| `InvalidPathError` | Class | Exception raised when a path attempts to escape the `root_dir`. |
| `PromptAccessError` | Class | Exception raised for IO or permission-related failures. |
| `PromptManager` | Class | The primary controller for prompt lifecycle management. |
| `__init__` | Method | Initializes the manager with a resolved `root_dir` and an optional logger. |
| `_log` | Method | Internal utility for safe, non-breaking logging via the provided logger. |
| `_resolve_prompt_path` | Method | Validates and resolves a string path into an absolute `.md` file path, preventing traversal. |
| `list_prompts` | Method | Scans the `root_dir` (or subfolder) for `.md` files and returns metadata. |
| `load_prompt` | Method | Reads and returns the string content of a specific prompt file. |
| `save_prompt` | Method | Writes content to a file, creating parent directories if necessary. |
| `read_prompt` | Method | Alias for `load_prompt`. |
| `create_prompt` | Method | Alias for `save_prompt`; returns a success message. |
| `update_prompt` | Method | Alias for `save_prompt`; returns a success message. |
| `delete_prompt` | Method | Removes a specific prompt file from the filesystem. |

## 4. Execution Logic & Flow
- **Initialization**: The `PromptManager` is instantiated with a `root_dir`. The path is immediately passed through `.resolve()` to establish a canonical absolute base for all subsequent security checks.
- **Data Path (Retrieval)**: 
    1. Input: `prompt_path` (string).
    2. Processing: `_resolve_prompt_path` checks for `..` components, appends `.md`, resolves the path, and verifies the resulting path starts with `root_dir`.
    3. Output: File content (string) or `PromptError` exception.
- **Data Path (Storage)**:
    1. Input: `prompt_path` (string) and `content` (string).
    2. Processing: Path resolution and validation $\rightarrow$ `mkdir` for parent directories $\rightarrow$ UTF-8 file write.
    3. Output: None (void) or `PromptAccessError`.
- **Conditional Branching**:
    - **Path Validation**: If `..` is detected in the path string or if the resolved path is outside the `root_dir`, an `InvalidPathError` is raised.
    - **Existence Checks**: Methods like `load_prompt` and `delete_prompt` branch to raise `PromptNotFoundError` if the resolved path does not exist on disk.
    - **Error Handling**: All IO operations are wrapped in `try-except` blocks that catch generic exceptions and re-raise them as specific `PromptAccessError` types to maintain API contract integrity.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib.Path`, `typing.List`, `typing.Dict`, `typing.Optional`, `typing.Any`, `typing.Tuple`, `os`
- **Internal Modules**: 
    - No internal modules imported.
- **External Packages**: None