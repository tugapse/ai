## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **FastAPI Application Factory** | [src/ai/modules/server/app.py](/AgentDocs/ai/modules/server/app.md) |

This component serves as the central orchestration point for the JARVIS Neural Hub web server. It is responsible for initializing the FastAPI application instance, configuring middleware, mounting static frontend assets, and wiring core business logic services into the application state.

The module acts as the primary entry point for the server-side API, providing endpoints for chat completions, health monitoring, and session/prompt management. It integrates several critical services, including the [ChatService](/AgentDocs/ai/modules/server/services/chat.md), [SessionManager](/AgentDocs/ai/modules/server/services/session_manager.md), and [PromptManager](/AgentDocs/ai/modules/server/services/prompt_manager.md), ensuring they are available to the request handlers via `app.state`.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `create_app(brain_hub: BrainHub, config: Dict[str, Any])` | Function | Initializes and returns a fully configured `FastAPI` instance. It wires `BrainHub`, `SessionManager`, `PromptManager`, and `ChatService` into the app state and mounts routers and static files. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The function `create_app` follows a dependency injection pattern where `BrainHub` and a configuration dictionary are passed in to initialize the server's internal state. It defines two primary API routes: `/api/v1/chat/completions` (and `/api/v1/chat`) for handling AI interactions, and `/api/health` for system status. It also dynamically mounts a frontend directory if it exists on the filesystem.
- **Side Effects:** 
    - **Filesystem:** Reads from the filesystem to locate session roots, prompt roots, and frontend static files.
    - **Network:** Configures CORS middleware to allow cross-origin requests from any origin (`*`).
    - **Logging:** Utilizes `ai.functions` to log initialization progress and debug incoming chat requests.
- **Error Handling:** 
    - Throws an `HTTPException` (500) if a request is made to the chat endpoint but the `ChatService` has not been properly initialized in the application state.
    - Relies on the [MIMETypeFixerMiddleware](/AgentDocs/ai/modules/server/middleware.md) to handle potential header issues during static file serving.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `config`  A dictionary passed to `create_app` containing global configuration settings required by the [ChatService](/AgentDocs/ai/modules/server/services/chat.md).

**Module Dependencies:**
- **Standard/External:** `pathlib`, `json`, `fastapi`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.modules.server.schemas](/AgentDocs/ai/modules/server/schemas.md)
    - [ai.modules.server.middleware](/AgentDocs/ai/modules/server/middleware.md)
    - [ai.modules.server.services.session_manager](/AgentDocs/ai/modules/server/services/session_manager.md)
    - [ai.modules.server.services.prompt_manager](/AgentDocs/ai/modules/server/services/prompt_manager.md)
    - [ai.modules.server.services.chat](/AgentDocs/ai/modules/server/services/chat.md)
    - [ai.modules.server.brain_hub](/AgentDocs/ai/modules/server/brain_hub.md)
    - [ai.modules.server.routers.sessions](/AgentDocs/ai/modules/server/routers/sessions.md)
    - [ai.modules.server.routers.prompts](/AgentDocs/ai/modules/server/routers/prompts.md)