## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **SessionManager** | [src/ai/modules/server/services/session_manager.py](/src/ai/modules/server/services/session_manager.py) |

The `SessionManager` is responsible for the lifecycle management of application sessions. It provides a robust interface for loading, saving, listing, and deleting session data, which is persisted as individual JSON files within a structured directory hierarchy.

Within the broader application architecture, this component acts as a server-side service. It ensures that session data is handled securely by preventing directory traversal attacks and provides a standardized way for the API layer (such as [src/ai/modules/server/routers/sessions.py](/src/ai/modules/server/routers/sessions.md)) to interact with persistent user state.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SessionError` | Exception | Base exception for all session-related errors. |
| `SessionNotFoundError` | Exception | Raised when a requested session file does not exist. |
| `InvalidPathError` | Exception | Raised when a provided path attempts to escape the root session directory. |
| `SessionAccessError` | Exception | Raised on generic IO or filesystem access errors. |
| `SessionManager(root_dir, logger)` | Class | Main service class. Initializes with a `Path` root directory and an optional callable logger. |
| `list_sessions(session_folder=None)` | Method | Scans the root or a sub-folder for `.json` files and returns a list of metadata dictionaries, sorted by modification time (newest first). |
| `load_session(session_path)` | Method | Loads and returns the full dictionary content of a specific session file. |
| `save_session(session_path, data)` | Method | Creates or overwrites a session file with the provided dictionary data. |
| `update_session_content(session_path, content)` | Method | Overwrites the entire content of an existing session file. |
| `update_session_title(session_path, title)` | Method | Performs a partial update on the `session_title` field within a session JSON file. |
| `delete_session(session_path)` | Method | Removes the specified session file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses `pathlib` for filesystem operations. It implements a security check in `_resolve_session_path` that resolves paths to their absolute form and verifies they remain within the `root_dir` prefix to prevent directory traversal. Metadata extraction during `list_sessions` is performed by reading the JSON content of each file found via `rglob`.
- **Side Effects:** This component performs significant filesystem I/O, including reading, writing, creating directories (`mkdir`), and deleting files (`unlink`). It also interacts with the provided `logger` callback for audit and error logging.
- **Error Handling:** The class uses a hierarchy of custom exceptions (`SessionError` and its subclasses) to allow callers to distinguish between missing files, security violations, and corrupted data. It also includes internal try-except blocks to prevent individual corrupted JSON files from crashing the `list_sessions` operation.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `typing`, `json`.
- **Internal:** No internal module imports are present in this file.