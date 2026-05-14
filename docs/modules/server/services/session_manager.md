## 1. Architectural Role

**Functional Mission**
The **SessionManager** class serves as the persistent storage controller for user interaction states. Its primary mission is to provide a secure, filesystem-based abstraction layer for managing session metadata and content, ensuring that conversational contexts are serialized into JSON format and protected against directory traversal attacks.

**System Context & Integration**
This component acts as a critical data persistence service within the server architecture, likely utilized by [chat](/docs/modules/server/services/chat.md) or orchestration modules to maintain continuity between discrete requests. It bridges the gap between volatile in-memory state and permanent storage, providing the necessary CRUD operations (Create, Read, Update, Delete) that allow downstream modules to retrieve historical context or save current session progress.

## 2. Environment & Configuration

**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `indent=4` (Default: `4`)  Used in `json.dump` to ensure human-readable session files.
- `encoding="utf-8"` (Default: `"utf-8"`)  Standardized character encoding for all filesystem I/O operations.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionError` | Class | Base exception for all session-related failures. |
| `SessionNotFoundError` | Class | Raised when a requested session file is missing from the filesystem. |
| `InvalidPathError` | Class | Raised when a path resolution attempt violates the `root_dir` boundary. |
| `SessionAccessError` | Class | Raised during low-level I/O or permission failures. |
| `SessionManager` | Class | The primary controller for session lifecycle and filesystem interaction. |
| `_log` | Method | Internal utility for dispatching debug/info messages to an optional logger. |
| `_resolve_session_path` | Method | Validates and converts a string path into a secure, absolute `Path` object. |
| `list_sessions` | Method | Scans the `root_dir` (and optionally subfolders) to return a list of session metadata. |
| `load_session` | Method | Retrieves and parses the full JSON content of a specific session. |
| `save_session` | Method | Writes a complete dictionary to a new or existing session file. |
| `update_session_content` | Method | Overwrites the existing content of a specific session file. |
| `update_session_title` | Method | Performs a partial update on the `session_title` key within a session file. |
| `delete_session` | Method | Removes the session file from the filesystem. |

## 4. Execution Logic & Flow

- **Initialization**: The `SessionManager` is instantiated with a `root_dir` (converted to an absolute `Path` via `.resolve()`) and an optional `logger` callback.
- **Data Path**:
    - **Input**: A `session_path` string or a `data` dictionary.
    - **Processing**: 
        1. Path resolution via `_resolve_session_path`.
        2. Security check: Verifies the resolved path starts with the `root_dir` string to prevent traversal.
        3. Suffix enforcement: Automatically appends `.json` to the path.
        4. I/O: Performs `json.load` or `json.dump` operations.
    - **Output**: Returns parsed `Dict` objects for reads, or `None` for writes/deletes.
- **Conditional Branching**:
    - **Path Validation**: If `resolved` path does not start with `root_dir`, an `InvalidPathError` is raised.
    - **File Existence**: Methods like `load_session` and `delete_session` check `.exists()` and `.is_file()` before proceeding, raising `SessionNotFoundError` if absent.
    - **Error Handling**: `list_sessions` uses a `try-except` block inside its loop to skip corrupted JSON files (`JSONDecodeError`) without halting the entire listing process.

## 5. Resource Dependencies

- **Standard Libraries**: `pathlib.Path`, `typing.List`, `typing.Dict`, `typing.Optional`, `typing.Any`, `typing.Tuple`, `json`
- **Internal Modules**: 
    - No direct internal module imports identified in the provided source.
- **External Packages**: None identified.