## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **SessionManager** | [src/ai/modules/server/services/session_manager.py](/AgentDocs/ai/modules/server/services/session_manager.md) |

The `SessionManager` is responsible for the persistence and lifecycle management of application sessions. It provides a structured way to store, retrieve, list, and delete session data, which is serialized as JSON files within a designated root directory on the filesystem.

Within the broader application architecture, this component serves as a backend service for the server module. It ensures that user or agent session states can be maintained across different execution contexts by providing a secure and validated interface for filesystem-based JSON storage.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SessionError` | Exception | Base exception for all session-related errors. |
| `SessionNotFoundError` | Exception | Raised when a requested session file does not exist. |
| `InvalidPathError` | Exception | Raised when a provided path attempts to escape the root session directory (directory traversal protection). |
| `SessionAccessError` | Exception | Raised on generic IO or filesystem access errors. |
| `SessionManager(root_dir: Path, logger: Optional[Any])` | Class | Initializes the manager with a base directory and an optional logging callback. |
| `list_sessions(session_folder: Optional[str])` | Method | Scans the root or a sub-folder for `.json` files and returns a list of metadata dictionaries, sorted by modification time (newest first). |
| `load_session(session_path: str)` | Method | Loads and returns the full dictionary content of a session file at the specified path. |
| `save_session(session_path: str, data: Dict)` | Method | Creates or overwrites a session file with the provided dictionary data. |
| `update_session_content(session_path: str, content: Dict)` | Method | Overwrites the entire content of an existing session file. |
| `update_session_title(session_path: str, title: str)` | Method | Updates only the `session_title` field within an existing session JSON file. |
| `delete_session(session_path: str)` | Method | Removes the specified session file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses `pathlib` for robust path manipulation. It implements a security check in `_resolve_session_path` to ensure that any requested `session_path` (after being converted to a `.json` file) resolves to a location strictly within the `root_dir`. This prevents directory traversal attacks.
- **Side Effects:** 
    - **Filesystem IO:** Performs extensive read, write, and delete operations on the local filesystem.
    - **Directory Creation:** `save_session` will automatically create parent directories if they do not exist.
    - **Logging:** If a callable `logger` is provided during initialization, the component will emit log messages regarding file access and errors.
- **Error Handling:** The component uses a hierarchy of custom exceptions (`SessionError` and its subclasses) to allow callers to differentiate between missing files, security violations (path escapes), and corrupted data (JSON decoding errors).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `typing`, `json`.
- **Internal:** No internal module dependencies found in the provided source.