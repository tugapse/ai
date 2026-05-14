## 1. Architectural Role

**Functional Mission**
The **app.py** component serves as the central orchestration layer for the FastAPI web server, acting as the primary entry point for all HTTP-based interactions with the JARVIS Neural Hub. Its mission is to expose a structured RESTful API that manages the lifecycle of chat sessions, prompt templates, and model configurations, effectively bridging the gap between external client requests and the internal intelligence services.

**System Context & Integration**
This module functions as the interface layer of the server architecture, consuming high-level business logic from [ChatService](/docs/modules/server/services/chat.md), [SessionManager](/docs/modules/server/services/session_manager.md), and [PromptManager](/docs/modules/server/services/prompt_manager.md). It integrates the [BrainHub](/docs/modules/server/brain_hub.md) to facilitate real-time chat completions and utilizes [MIMETypeFixerMiddleware](/docs/modules/server/middleware.md) to ensure correct data delivery. By mounting a static frontend and configuring CORS, it transforms the core AI logic into a fully accessible web application.

## 2. Environment & Configuration

**Environment Lookups:**
- `func.get_root_directory()`  Retrieves the base filesystem path for locating sessions, prompts, and models.

**Hardcoded Constants:**
- `SESSION_ROOT_DIR` (Default: `root/sessions/server`)  Base directory for session storage.
- `PROMPT_ROOT_DIR` (Default: `root/system`)  Base directory for system prompt templates.
- `MODEL_CONFIG_DIR` (Default: `root/models`)  Directory containing JSON model configuration files.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `create_app` | Func | Factory function that instantiates, configures, and returns the `FastAPI` application instance. |
| `get_sessions` | Func | GET endpoint to list available chat sessions, with optional sub-folder filtering. |
| `get_session_content` | Func | GET endpoint to retrieve the full content of a specific session file. |
| `update_session_content` | Func | PUT endpoint to overwrite the entire content of a session. |
| `update_session_title` | Func | PUT endpoint to modify only the metadata title of a session. |
| `delete_session` | Func | DELETE endpoint to remove a session file from storage. |
| `get_prompts` | Func | GET endpoint to list available prompt templates. |
| `get_prompt_content` | Func | GET endpoint to read the text content of a specific prompt. |
| `get_model_configs` | Func | GET endpoint to scan the models directory and return a list of available model JSON configurations. |
| `create_prompt` | Func | POST endpoint to persist a new prompt template to disk. |
| `update_prompt_content` | Func | PUT endpoint to modify an existing prompt template. |
| `delete_prompt` | Func | DELETE endpoint to remove a prompt template. |
| `chat_completions` | Func | POST endpoint (aliased for `/api/v1/chat`) to trigger the AI chat logic via `ChatService`. |
| `health` | Func | GET endpoint to verify service availability and report the active model name. |

## 4. Execution Logic & Flow

- **Initialization**:
    1. Receives `brain_hub` and `config` dependencies.
    2. Resolves filesystem paths for sessions, prompts, and models using `func.get_root_directory()`.
    3. Instantiates `SessionManager`, `PromptManager`, and `ChatService`.
    4. Initializes `FastAPI` instance and applies `MIMETypeFixerMiddleware` and `CORSMiddleware`.
    5. Mounts the frontend static files if the directory exists.
- **Data Path (Chat Completion)**:
    1. **Input**: `ChatCompletionRequest` (JSON) containing model, system prompt, and session info.
    2. **Processing**: The request is logged via `func.debug`, then passed to `chat_service.chat_completion`.
    3. **Output**: Returns a stream or a completed JSON response from the `ChatService`.
- **Conditional Branching**:
    - **Path Validation**: Every session/prompt endpoint checks for `SessionNotFoundError`, `PromptNotFoundError`, or `InvalidPathError` to return appropriate 404 or 400 HTTP status codes.
    - **Dependency Check**: Validates if managers (session/prompt/chat) are `None` before execution, raising 500 errors if misconfigured.
    - **Static Files**: Checks for the existence of `FRONTEND_BUILD_DIR` before attempting to mount the static application.

## 5. Resource Dependencies

- **Standard Libraries**: `pathlib`, `json`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [ChatCompletionRequest](/docs/modules/server/schemas.md)
    - [UpdateSessionRequest](/docs/modules/server/schemas.md)
    - [PromptCreateRequest](/docs/modules/server/schemas.md)
    - [PromptUpdateRequest](/docs/modules/server/schemas.md)
    - [MIMETypeFixerMiddleware](/docs/modules/server/middleware.md)
    - [SessionManager](/docs/modules/server/services/session_manager.md)
    - [PromptManager](/docs/modules/server/services/prompt_manager.md)
    - [ChatService](/docs/modules/server/services/chat.md)
    - [BrainHub](/docs/modules/server/brain_hub.md)
- **External Packages**: `fastapi`, `starlette` (via FastAPI)