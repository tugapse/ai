## 1. Architectural Role
This file serves as the central orchestration layer for the FastAPI web server, responsible for bootstrapping the application and exposing a RESTful API surface. It integrates core business logic by wiring together [brain_hub.md](modules/server/brain_hub.md), [session_manager.md](modules/server/services/session_manager.md), [prompt_manager.md](modules/server/services/prompt_manager.md), and [chat.md](modules/server/services/chat.md) into a unified interface. The module manages the lifecycle of session/prompt CRUD operations, model configuration retrieval, and asynchronous chat completions while handling static frontend delivery and cross-cutting concerns via [middleware.md](modules/server/middleware.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `config` (via `create_app` parameter)  Injected dictionary containing application-wide settings.
- `func.get_root_directory()` (via `functions.md`)  Determines the base filesystem path for sessions, prompts, and models.

**Hardcoded Constants:**
- `SESSION_ROOT_DIR` (Default: `root/sessions/server`)  Filesystem path for session storage.
- `PROMPT_ROOT_DIR` (Default: `root/system`)  Filesystem path for system prompt storage.
- `MODEL_CONFIG_DIR` (Default: `root/models`)  Filesystem path for model JSON configurations.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `create_app` | Func | Primary factory function that instantiates FastAPI and injects dependencies. |
| `/api/v1/sessions` | GET | Lists available session directories/files. |
| `/api/v1/sessions/{path}` | GET | Retrieves specific session content. |
| `/api/v1/sessions/{path}` | PUT | Overwrites full session content via `UpdateSessionRequest`. |
| `/api/v1/sessions/{path}/title` | PUT | Updates only the metadata title of a session. |
| `/api/v1/sessions/{path}` | DELETE | Removes a session file from the filesystem. |
| `/api/v1/prompts` | GET | Lists available prompts. |
| `/api/v1/prompts/{path}` | GET | Reads specific prompt content. |
| `/api/v1/prompts` | POST | Creates a new prompt file using `PromptCreateRequest`. |
| `/api/v1/prompts/{path}` | PUT | Updates existing prompt content via `PromptUpdateRequest`. |
| `/api/v1/prompts/{path}` | DELETE | Removes a prompt file. |
| `/api/v1/model-configs` | GET | Scans `MODEL_CONFIG_DIR` and returns parsed model JSON metadata. |
| `/api/v1/chat` | POST | Entry point for AI interaction (streaming or non-streaming). |
| `/api/v1/chat/completions` | POST | Alias for chat completion requests. |
| `/api/health` | GET | Returns system status and current model name from `brain_hub`. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. `create_app` receives `brain_hub` and `config`.
    2. Path constants are calculated using `func.get_root_directory()`.
    3. Service instances (`SessionManager`, `PromptManager`, `ChatService`) are instantiated.
    4. FastAPI app is created; Middleware (`MIMETypeFixerMiddleware`, `CORSMiddleware`) is applied.
    5. Frontend static files are mounted to `/` if the directory exists.
- **Data Path (Chat)**: 
    `Request (ChatCompletionRequest)` $\rightarrow$ `chat_service.chat_completion()` $\rightarrow$ `brain_hub` interaction $\rightarrow$ `Response (Stream/JSON)`.
- **Data Path (Config Retrieval)**: 
    `GET /api/v1/model-configs` $\rightarrow$ `rglob("*.json")` $\rightarrow$ `json.load()` $\rightarrow$ `List[Dict]`.
- **Conditional Branching**:
    - **Frontend Presence**: If `FRONTEND_BUILD_DIR` is a directory, mount `StaticFiles`.
    - **Manager Availability**: Check if `session_manager` or `prompt_manager` is `None` before executing CRUD (throws 500).
    - **Error Handling**: Specific catch blocks for `SessionNotFoundError`, `PromptNotFoundError`, and `InvalidPathError` to return 404 or 400 status codes respectively.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib`, `json`, `typing`
- **Internal Modules**: 
    - [functions.md](functions.md)
    - [schemas.md](modules/server/schemas.md)
    - [middleware.md](modules/server/middleware.md)
    - [session_manager.md](modules/server/services/session_manager.md)
    - [prompt_manager.md](modules/server/services/prompt_manager.md)
    - [chat.md](modules/server/services/chat.md)
    - [brain_hub.md](modules/server/brain_hub.md)
- **External Packages**: `fastapi`, `fastapi.staticfiles`, `fastapi.middleware.cors`