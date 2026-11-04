## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **JARVIS Neural Hub Server** | [src/ai/modules/server/app.py](/src/ai/modules/server/app.py) |

The `app.py` module serves as the central orchestration point for the JARVIS Neural Hub's FastAPI web server. Its primary responsibility is to initialize the web application, wire together essential backend servicessuch as session management, prompt management, and chat servicesand expose them via RESTful API endpoints.

Within the broader architecture, this component acts as the primary interface between the internal AI logic and external clients (such as web frontends or mobile applications). It manages the lifecycle of the API, configures middleware for CORS and MIME type handling, and mounts static assets to serve the frontend application.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `create_app(brain_hub: BrainHub, config: Dict[str, Any])` | Function | Initializes, configures, and returns a `FastAPI` instance with all necessary managers and services injected into `app.state`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `create_app` function performs dependency injection by instantiating `SessionManager`, `PromptManager`, and `ChatService`. These instances are attached to `app.state` to ensure they are accessible throughout the application lifecycle. It also integrates external routers for specific domains (sessions and prompts) and sets up a static file mount for the frontend.
- **Side Effects:** 
    - **Filesystem:** Accesses and reads from the filesystem to initialize session and prompt directories based on the root directory provided by `ai.functions`.
    - **Network:** Starts a web server (via FastAPI) to listen for incoming HTTP requests.
    - **Logging:** Utilizes `ai.functions` to log initialization sequences and debug information.
- **Error Handling:** 
    - Throws an `HTTPException` (500) if a request is made to the chat endpoints but the `ChatService` has not been correctly initialized in the application state.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `config` (Dict)  A dictionary passed to `create_app` containing global configuration settings required by the `ChatService`.

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