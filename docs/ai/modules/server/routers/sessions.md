## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Sessions Router |
| Source file | sessions.py |

The **Sessions Router** serves as the HTTP interface layer for managing persistent conversation states within the server module. It exposes a RESTful API that allows external clients to interact with the underlying session storage system, providing endpoints for discovery, retrieval, modification, and deletion of session data.

**Functional Mission**
The primary responsibility of this file is to act as a controller that translates incoming HTTP requests into actionable commands for the session management logic. It solves the problem of providing a standardized, networked way to manage the lifecycle of AI chat sessions, ensuring that session persistence is accessible via the web API.

**System Context & Integration**
This component sits at the edge of the server architecture, receiving requests through the FastAPI framework. It acts as a bridge between the network layer and the core business logic residing in [Session Manager](/docs/ai/modules/server/services/session_manager.md). When a request is received, the router extracts necessary parameters (like `session_path`) and delegates the heavy lifting to the `session_manager` instance stored in the application state. It is responsible for translating domain-specific exceptions from the service layer into appropriate HTTP status codes (404, 400, 500) for the client.

- **INTERNAL REFERENCES**: [Session Manager](/docs/ai/modules/server/services/session_manager.md), [UpdateSessionRequest](/docs/ai/modules/server/schemas.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `get_sessions` | Func | GET `/api/v1/sessions`: Lists available sessions, optionally filtered by a sub-folder. |
| `get_session_content` | Func | GET `/api/v1/sessions/{session_path:path}`: Retrieves the full content of a specific session. |
| `update_session_content` | Func | PUT `/api/v1/sessions/{session_path:path}`: Overwrites the entire content of a session using `UpdateSessionRequest`. |
| `update_session_title` | Func | PUT `/api/v1/sessions/{session_path:path}/title`: Updates only the metadata title of a session. |
| `delete_session` | Func | DELETE `/api/v1/sessions/{session_path:path}`: Permanently removes a session file from storage. |

## 4. Execution Logic & Flow
- **Initialization**: The router relies on the `request.app.state.session_manager` being pre-configured during the application startup sequence.
- **Data Path**: 
    1. **Input**: HTTP Request (Method + Path + Optional Query/Body).
    2. **Processing**: 
        - Validate existence of `session_manager` in app state.
        - Extract `session_path` or `payload` data.
        - Call corresponding method on `session_manager`.
    3. **Output**: JSON response containing session data, success messages, or error details.
- **Conditional Branching**:
    - **Manager Check**: If `session_manager` is `None`, returns `500 Internal Server Error`.
    - **Error Mapping**:
        - `SessionNotFoundError` $\rightarrow$ `404 Not Found`.
        - `SessionInvalidPathError` $\rightarrow$ `400 Bad Request`.
        - Generic `Exception` $\rightarrow$ `500 Internal Server Error`.
    - **Payload Validation**: In `update_session_content`, checks if `session_content` exists in the payload; if not, returns `400 Bad Request`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing.Optional`
- **Internal Modules**: 
    - [UpdateSessionRequest](/docs/ai/modules/server/schemas.md)
    - [SessionInvalidPathError](/docs/ai/modules/server/services/session_manager.md)
    - [SessionNotFoundError](/docs/ai/modules/server/services/session_manager.md)
- **External Packages**: `fastapi`