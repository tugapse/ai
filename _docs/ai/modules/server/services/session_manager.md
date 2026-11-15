## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| SessionManager | /ai/modules/server/services/session_manager.md |

This component is responsible for managing the complete lifecycle of application sessions. Its primary duty is to provide a robust, file-system-backed mechanism for creating, retrieving, updating, and deleting session states, which are serialized as JSON files within a designated root directory. It ensures data integrity by strictly controlling path resolution to prevent directory traversal attacks.

As a core service, `SessionManager` acts as the persistence layer for session data within the application's service architecture. It interfaces with the filesystem to store state, abstracting the complexities of file I/O, JSON serialization, and path validation away from higher-level logic components like a [Controller](/ai/modules/server/controllers/main_controller.md) or a [SessionService](/ai/modules/server/services/session_service.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| SessionError | Class | Base exception for session-related errors. |
| SessionNotFoundError | Class | Raised when a requested session file does not exist. |
| InvalidPathError | Class | Raised when a provided path would escape the root session directory. |
| SessionAccessError | Class | Raised on generic access/IO errors while handling sessions. |
| SessionManager | Class | Manages the lifecycle of application sessions. |
| list_sessions | Method | Lists all sessions (metadata) under the root directory, optionally filtered by a sub-folder. |
| load_session | Method | Loads a single session by its path, returning the full content. |
| save_session | Method | Saves or overwrites a session file with provided data. |
| update_session_content | Method | Overwrites the entire session content, handling both dict replacement and message list replacement. |
| update_session_title | Method | Updates only the session title field inside the JSON metadata. |
| delete_session | Method | Deletes a specific session file identified by its path. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `SessionManager` uses path manipulation (`pathlib.Path`) combined with strict prefix checking (`resolved.startswith(self.root_dir)`) within `_resolve_session_path` to enforce sandbox boundaries. Listing sessions recursively scans the designated root directory for JSON files, loads metadata, and sorts the results by modification time. Saving/Updating involves JSON serialization/deserialization to the resolved path.

- **Side Effects:** Reads and writes to the local filesystem (via `open`, `unlink`, `mkdir`).

- **Error Handling:** It uses a hierarchy of custom exceptions (`SessionError`, `SessionNotFoundError`, `InvalidPathError`, `SessionAccessError`) to categorize failures. JSON decoding errors are caught specifically during loading/updating and mapped to `SessionError`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `typing`, `json`.
- **Internal:** None.