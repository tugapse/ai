## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | SessionManager |
| Source file | session_manager.py |

The **SessionManager** serves as the persistent storage abstraction layer for user interaction sessions within the server module. It is responsible for the lifecycle management of session data, ensuring that conversational states, metadata, and session-specific configurations are safely serialized to and deserialized from the filesystem.

**Functional Mission**
The primary responsibility of **SessionManager** is to provide a secure, file-based persistence mechanism for session objects. It solves the problem of state volatility by translating in-memory session dictionaries into structured JSON files, while implementing strict path validation to prevent directory traversal attacks.

**System Context & Integration**
This component acts as a data access object (DAO) for the server's session-related logic. It is primarily utilized by [sessions.py](/docs/ai/modules/server/routers/sessions.md) to fulfill API requests regarding session listing, retrieval, and modification. By centralizing all I/O operations related to sessions, it ensures that the rest of the server architecture interacts with a consistent, validated interface rather than direct filesystem calls.

- **INTERNAL REFERENCES**: [sessions.py](/docs/ai/modules/server/routers/sessions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionError` | Class | Base exception for all session-related failures. |
| `SessionNotFoundError` | Class | Exception raised when a requested session file is missing. |
| `InvalidPathError` | Class | Exception raised when a path attempts to escape the `root_dir`. |
| `SessionAccessError` | Class | Exception raised for low-level I/O or permission errors. |
| `SessionManager` | Class | Main controller for session lifecycle and persistence. |
| `_log` | Method | Internal utility for dispatching debug/info messages to the provided logger. |
| `_resolve_session_path` | Method | Validates and converts a string path into a safe, absolute `Path` object. |
| `list_sessions` | Method | Scans the root directory (or subfolder) for `.json` files and returns metadata. |
| `load_session` | Method | Reads and parses a specific session JSON file into a dictionary. |
| `save_session` | Method | Creates or overwrites a session file with provided dictionary data. |
| `update_session_content` | Method | Performs a full overwrite of an existing session file. |
| `update_session_title` | Method | Performs a partial update of only the `session_title` field. |
| `delete_session` | Method | Removes a session file from the filesystem. |

## 4. Execution Logic & Flow
- **Initialization**: The manager is instantiated with a `root_dir` (converted to an absolute `Path`) and an optional `logger` callback.
- **Data Path**: 
    - **Input**: A string-based `session_path` or a dictionary of session data.
    - **Processing**: 
        1. Path resolution via `_resolve_session_path` (includes `startswith` check against `root_dir`).
        2. File I/O (reading/writing) using `utf-8` encoding.
        3. JSON serialization/deserialization.
    - **Output**: A dictionary representing session content or a list of metadata dictionaries.
- **Conditional Branching**:
    - **Path Validation**: If `resolved.startswith(self.root_dir)` is false, an `InvalidPathError` is raised.
    - **File Existence**: Methods like `load_session` and `delete_session` check `.exists()` and `.is_file()` before proceeding, raising `SessionNotFoundError` if absent.
    - **Error Handling**: `list_sessions` uses a `try-except` block inside its loop to skip corrupted JSON files without halting the entire listing process.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib`, `typing`, `json`
- **Internal Modules**: 
    - No direct internal module imports found in the provided source.
- **External Packages**: None identified.