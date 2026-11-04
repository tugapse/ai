## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Session Router** | [src/ai/modules/server/routers/sessions.py](/src/ai/modules/server/routers/sessions.py) |

This component provides a FastAPI router that exposes RESTful endpoints for managing AI interaction sessions. It acts as the interface between external clients and the underlying session persistence logic, allowing for the listing, retrieval, updating, and deletion of session data.

The router serves as a controller within the server module architecture. It relies on the `session_manager` attached to the FastAPI application state to perform all disk or database operations. By abstracting these operations behind standard HTTP methods (GET, PUT, DELETE), it enables remote management of conversation histories and session states.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `get_sessions` | Function | `GET /api/v1/sessions`. Retrieves a list of available sessions, optionally filtered by a sub-folder path. |
| `get_session_content` | Function | `GET /api/v1/sessions/{session_path:path}`. Retrieves the full content of a specific session file via its path. |
| `update_session_content` | Function | `PUT /api/v1/sessions/{session_path:path}`. Overwrites the entire content of a session using the provided `UpdateSessionRequest` payload. |
| `update_session_title` | Function | `PUT /api/v1/sessions/{session_path:path}/title`. Updates only the title metadata of a session. |
| `delete_session` | Function | `DELETE /api/v1/sessions/{session_path:path}`. Permanently removes a session file from the system. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router delegates all business logic to `request.app.state.session_manager`. It extracts the manager from the application state, validates the presence of required payload fields (like `session_content` or `session_title`), and maps service-layer exceptions to appropriate HTTP status codes.
- **Side Effects:** 
    - **Filesystem/Persistence:** The `update_session_content`, `update_session_title`, and `delete_session` endpoints trigger write or delete operations via the session manager.
    - **Network:** Responds to HTTP requests and returns JSON payloads.
- **Error Handling:** 
    - `404 Not Found`: Raised when a requested `session_path` does not exist.
    - `400 Bad Request`: Raised when the provided path is invalid or required payload fields are missing.
    - `500 Internal Server Error`: Raised if the `session_manager` is unconfigured or if an unexpected exception occurs during processing.
    - Maps `SessionNotFoundError` and `SessionInvalidPathError` from the service layer to specific HTTP responses.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `fastapi`, `typing`.
- **Internal:**
    - [UpdateSessionRequest](/AgentDocs/ai/modules/server/schemas.md)
    - [SessionInvalidPathError](/AgentDocs/ai/modules/server/services/session_manager.md)
    - [SessionNotFoundError](/AgentDocs/ai/modules/server/services/session_manager.md)