## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Pipelines | ai/modules/server/services/pipelines.md |

This component is responsible for managing the lifecycle of execution pipelines used within the web editor. Its primary function is to provide robust mechanisms for locating, reading, validating, saving, creating, and deleting pipeline definitions. It enforces structure and integrity checks on pipeline content to ensure they are executable and conform to expected schemas.

Architecturally, this file acts as a core service layer within the backend. It interfaces with the `DirectoryManager` (specifically accessing user and system pipeline directories) to handle file system persistence. It serves as the authoritative API for pipeline manipulation, coordinating validation against known tools and targets before any write operation occurs.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `PipelineError` | Class | Custom exception used to signal pipeline-related errors, carrying an HTTP status code and detail message. |
| `_folders()` | Function | Helper to return a list of tuples containing pipeline source ('user' or 'system') and their respective directory paths. |
| `_check_name()` | Function | Validates that a given name string conforms to the allowed naming pattern (letters, digits, '_', '-'). |
| `locate()` | Function | Finds the source and full path of an existing pipeline by name, prioritizing the user pipeline folder. |
| `read()` | Function | Reads the content of a pipeline file, returning a dictionary containing its name, source, and parsed JSON content. |
| `validate()` | Function | Performs comprehensive validation on pipeline content, checking schema integrity, agent configurations, and tool references. Returns warnings if any tools are unknown. |
| `_write()` | Function | Atomically writes content to a specified path, ensuring directory existence and using a temporary file for safety. |
| `save()` | Function | Overwrites an existing pipeline file in its original source location after validating the new content. |
| `create()` | Function | Creates a new pipeline file specifically in the user pipeline folder, raising an error if a pipeline with the same name already exists anywhere. |
| `delete()` | Function | Removes a specified pipeline file from the filesystem, with a guard against deleting the 'default' pipeline. |
| `list_tools()` | Function | Aggregates and returns a list of all available tools, combining those provided by loaded modules and user-defined tools, along with metadata like permission requirements. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses `locate` to determine the file path, which dictates whether the pipeline is read/saved to the user or system folder. `validate` executes a multi-step check: ensuring top-level structure (`agents`, `entry_point`), validating agent names and prompt file paths against the system directory, and checking tool references against `known_tools`. File writing is done atomically via a temporary file swap (`os.replace`).
- **Side Effects:** Extensive filesystem interaction occurs through `os.path.isfile`, `open`, `os.makedirs`, `os.replace`, and `os.remove` during `locate`, `read`, `_write`, `create`, and `delete`. It also interacts with external tool loading mechanisms within `list_tools`.
- **Error Handling:** It raises `PipelineError` (with appropriate HTTP status codes like 400 for validation failures, 404 for not found, 409 for conflicts, and 500 for I/O errors) across all major public functions.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `os`, `re`, `typing`.
- **Internal:** [ai.services.directory_manager](/ai/modules/server/services/directory_manager.md), [ai.tools.tool_loader](/ai/tools/tool_loader.md), [ai.tools.tool_registry](/ai/tools/tool_registry.md).