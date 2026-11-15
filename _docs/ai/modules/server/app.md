## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| app | /ai/modules/server/app.md |

This component serves as the main entry point and orchestration layer for the entire backend API server built with FastAPI. Its primary responsibility is to initialize, configure, and wire together all necessary application services—such as session management, prompt handling, chat logic, and authentication—into a cohesive, runnable application instance. It defines the core API endpoints that clients use to interact with the AI backend.

Architecturally, this file acts as the central controller and application bootstrap. It instantiates and registers managers ([SessionManager](/ai/modules/server/services/session_manager.md), [PromptManager](/ai/modules/server/services/prompt_manager.md)), the [ChatService](/ai/modules/server/services/chat.md), and the [BrainHub](/ai/modules/server/brain_hub.md) into the FastAPI application state. It also mounts the static frontend assets and configures cross-origin resource sharing (CORS) policies.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| create_app | Function | Builds and configures the FastAPI app, wiring dependencies into app.state. Takes `brain_hub`, `config`, `modules`, and `auth` as arguments. |
| chat_completions | Function | Handles incoming requests for chat completions, delegating the processing to the configured `ChatService`. |
| health | Function | Provides a health check endpoint, returning the server status, loaded model, and available models. |
| stats | Function | Returns token usage statistics from the loaded model via the `BrainHub`. |
| unload_model | Function | Frees the currently loaded AI model from memory (RAM/VRAM) based on a device authorization. |
| shutdown | Function | Initiates a graceful shutdown of the server and unloads the model, triggered by an authorized device. |
| SameHostCORSMiddleware | Class | Custom middleware that enforces CORS rules, allowing connections from configured origins plus any origin matching the server's hostname. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `create_app` function initializes the application structure, sets up dependency injection via `app.state`, and mounts routers for various functionalities (sessions, prompts, agent runs). The application logic relies heavily on dependency resolution and service orchestration to handle requests like `/api/v1/chat/completions`.
- **Side Effects:** The code interacts extensively with the filesystem (for session and prompt directories), performs network operations (via FastAPI/CORS middleware), and mutates application state (e.g., loading/unloading models in `BrainHub`).
- **Error Handling:** Raises `HTTPException` for invalid states, such as when the chat service is not configured, or when attempting to unload/shutdown while the agent or model is busy (returning HTTP 409 Conflict).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- None specified for global environment variables, though the configuration dictionary passed to `create_app` dictates behavior.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `json`, `asyncio`, `urllib.parse`, `fastapi`, `fastapi.staticfiles`, `fastapi.middleware.cors`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.modules.server.schemas.ChatCompletionRequest](/ai/modules/server/schemas.md), [ai.modules.server.schemas.UpdateSessionRequest](/ai/modules/server/schemas.md), [ai.modules.server.schemas.PromptCreateRequest](/ai/modules/server/schemas.md), [ai.modules.server.schemas.PromptUpdateRequest](/ai/modules/server/schemas.md), [ai.modules.server.middleware.MIMETypeFixerMiddleware](/ai/modules/server/middleware.md), [ai.modules.server.services.session_manager.SessionManager](/ai/modules/server/services/session_manager.md), [ai.modules.server.services.session_manager.SessionNotFoundError](/ai/modules/server/services/session_manager.md), [ai.modules.server.services.session_manager.InvalidPathError](/ai/modules/server/services/session_manager.md), [ai.modules.server.services.prompt_manager.PromptManager](/ai/modules/server/services/prompt_manager.md), [ai.modules/server/services/prompt_manager.PromptNotFoundError](/ai/modules/server/services/prompt_manager.md), [ai.modules/server/services/prompt_manager.PromptAccessError](/ai/modules/server/services/prompt_manager.md), [ai.modules/server/services/chat.ChatService](/ai/modules/server/services/chat.md), [ai.modules/server/brain_hub.BrainHub](/ai/modules/server/brain_hub.md), [ai.modules/server.services.frontend.API_LEVEL](/ai/modules/server/services/frontend.md), [ai.modules/server.routers.sessions.router](/ai/modules/server/routers/sessions.md), [ai.modules/server.routers.prompts.router](/ai/modules/server/routers/prompts.md), [ai.modules/server.routers.agent.router](/ai/modules/server/routers/agent.md), [ai.modules/server.routers.auth.router](/ai/modules/server/routers/auth.md), [ai.modules/server.services.auth.AuthService](/ai/modules/server/services/auth.md), [ai.modules/server.services.agent_runs.AgentRunService](/ai/modules/server/services/agent_runs.md)