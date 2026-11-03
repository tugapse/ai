## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **sessions router** | [src/ai/modules/server/routers/sessions.py](/AgentDocs/ai/modules/server/routers/sessions.md) |

This component provides a FastAPI router responsible for managing the lifecycle and retrieval of saved AI sessions. It exposes a RESTful API that allows clients to list available sessions, retrieve specific session contents, update session data (either full content or just the title), and delete session files.

As a controller within the server module, it acts as the interface between external HTTP requests and the internal session management logic. It relies heavily on the `session_manager` attached to the FastAPI application state to perform actual filesystem or database operations, ensuring a separation of concerns between API routing and data persistence.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `get_sessions` | Function | `GET /api/v1/sessions`. Retrieves a list of sessions, optionally filtered by a `session_folder` path. |
| `get_session_content` | Function | `GET /api/v1/sessions/{session_path:path}`. Returns the full content of a session located at the specified path. |
| `update_session_content` | Function | `PUT /api/v1/sessions/{session_path:path}`. Overwrites the content of an existing session using the `UpdateSessionRequest` payload. |
| `update_session_title` | Function | `PUT /api/v1/sessions/{session_path:path}/title`. Updates only the title metadata of a session using the `UpdateSessionRequest` payload. |
| `delete_session` | Function | `DELETE /api/v1/sessions/{session_path:path}`. Permanently removes the session file at the specified path. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router functions as a thin wrapper around the `session_manager`. It extracts the `session_manager` from `request.app.state`, validates the presence of the manager, and maps service-layer exceptions (like `SessionNotFoundError` or `SessionInvalidPathError`) to appropriate HTTP status codes (404, 400, or 500).
- **Side Effects:** 
    - **Filesystem Interaction:** Through the `session_manager`, this router triggers reads, writes, and deletions of session files on the host system.
    - **State Access:** Reads from the FastAPI `app.state` to access the shared `session_manager` instance.
- **Error Handling:** 
    - `404 Not Found`: Raised when a requested session path does not exist.
    - `400 Bad Request`: Raised when a provided path is invalid or required payload fields (like `session_content` or `session_title`) are missing.
    - `500 Internal Server Error`: Raised if the `session_manager` is unconfigured or if an unhandled exception occurs during I/O operations.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `fastapi`, `typing`.
- **Internal:**
    - [UpdateSessionRequest](/AgentDocs/ai/modules/server/schemas.md)
    - [SessionInvalidPathError](/AgentDocs/ai/modules/server/services/session_manager.md)
    - [SessionNotFoundError](/AgentDocs/ai/modules/server/services/session_manager.md)