## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| sessions | /ai/modules/server/routers/sessions.md |

This component defines the RESTful API endpoints for managing user sessions. Its primary responsibility is to provide CRUD-like operations—listing, retrieving content, updating titles, updating content, and deleting sessions—through HTTP requests. It acts as the entry point for client interactions related to persistent session data.

This router sits at the presentation/controller layer of the application architecture. It relies heavily on the `session_manager` service, which is injected via the FastAPI `Request` object and is responsible for the actual business logic and filesystem interactions. It uses security dependencies defined in [ai/modules/server/routers/auth.md] to enforce access control.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| get_sessions | Function | Retrieves a list of saved sessions, optionally filtered by a sub-folder. |
| get_session_content | Function | Retrieves the content of a specific saved session identified by its path. |
| update_session_title | Function | Updates only the session title for a specified session path. |
| update_session_content | Function | Overwrites the entire session content for a specified session path. |
| delete_session | Function | Deletes a specific session file identified by its path. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router delegates all core session management logic (listing, loading, updating, deleting) to the `session_manager` instance retrieved from the request state. It handles path parsing, dependency checks (e.g., `require_device`), and input validation based on the `UpdateSessionRequest` schema. Specific logic is implemented for content updates to handle both dict/object and list-of-message formats.
- **Side Effects:** Reads and writes to the filesystem via the `session_manager` service when loading, updating, or deleting sessions.
- **Error Handling:** It catches specific exceptions from the session manager (`SessionNotFoundError`, `SessionInvalidPathError`) and maps them to appropriate HTTP status codes (404, 400). Generic exceptions are caught and mapped to a 500 Internal Server Error.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `fastapi`, `typing`
- **Internal:** [ai/modules/server/routers/auth.md]
- **Internal:** [ai/modules/server/schemas.md]
- **Internal:** [ai/modules/server/services/session_manager.md]