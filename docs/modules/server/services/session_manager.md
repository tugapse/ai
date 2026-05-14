## 1. Architectural Role
Provides a secure, filesystem-based persistence layer for managing JSON-encoded session metadata and content via path-validated CRUD operations.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionError` | Class | Base exception for all session-related failures. |
| `SessionNotFoundError` | Class | Exception raised when a requested session file is missing. |
| `InvalidPathError` | Class | Exception raised when a path attempts to escape the `root_dir`. |
| `SessionAccessError` | Class | Exception raised for IO or permission-related failures. |
| `SessionManager` | Class | Orchestrator for session lifecycle and filesystem interaction. |
| `_log` | Method | Internal utility for conditional execution of the `logger` callback. |
| `_resolve_session_path` | Method | Validates and transforms string paths into absolute, sandboxed `.json` paths. |
| `list_sessions` | Method | Recursively scans `root_dir` for `.json` files and returns metadata. |
| `load_session` | Method | Retrieves and parses the full JSON content of a specific session. |
| `save_session` | Method | Persists a dictionary to a new or existing JSON file. |
| `update_session_content` | Method | Overwrites existing session file content with a new dictionary. |
| `update_session_title` | Method | Performs a partial update of the `session_title` key within a JSON file. |
| `delete_session` | Method | Removes a session file from the filesystem. |

## 3. Execution Logic & Flow
- **Initialization**:
    1. Receives `root_dir` and an optional `logger`.
    2. Resolves `root_dir` to an absolute path via `Path.resolve()`.
    3. Stores the resolved path and logger instance in the object state.
- **Data Path**:
    - **Input**: String-based `session_path` or `session_folder`.
    - **Processing**: 
        1. Path resolution and suffix appending (`.json`).
        2. Directory traversal validation (checking if `resolved` starts with `root_dir`).
        3. Filesystem IO (read/write/unlink).
        4. JSON serialization/deserialization.
    - **Output**: Dictionary (metadata or full content), List of Dictionaries (session list), or None (void operations).
- **Conditional Branching**:
    - **Path Validation**: If `resolved` path is outside `root_dir`, raise `InvalidPathError`.
    - **Existence Check**: If file does not exist during `load`, `update`, or `delete`, raise `SessionNotFoundError`.
    - **JSON Integrity**: If `json.load` fails, raise `SessionError` (corrupted file) or log and skip (during `list_sessions`).
    - **Logger Availability**: If `self.logger` is not callable, skip logging operations.

## 4. Resource Dependencies
- **Standard Libraries**: `pathlib.Path`, `typing.List`, `typing.Dict`, `typing.Optional`, `typing.Any`, `typing.Tuple`, `json`.
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - File extension: `.json`.
    - JSON formatting: `indent=4`.
    - Encoding: `utf-8`.
- **Environment Lookups**: None.