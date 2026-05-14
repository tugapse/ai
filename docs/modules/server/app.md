## 1. Architectural Role
Acts as the FastAPI application factory that orchestrates the assembly of the neural hub's web interface, wiring session, prompt, and chat services into a unified RESTful API.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `create_app` | Func | Initializes the FastAPI instance, configures directory paths, instantiates managers, and mounts middleware/static files. |
| `/api/v1/sessions` | GET | Lists available sessions, optionally filtered by `session_folder`. |
| `/api/v1/sessions/{session_path:path}` | GET | Retrieves specific session content via `session_manager.load_session`. |
| `/api/v1/sessions/{session_path:path}` | PUT | Overwrites session content using `UpdateSessionRequest`. |
| `/api/v1/sessions/{session_path:path}/title` | PUT | Updates only the session title via `UpdateSessionRequest`. |
| `/api/v1/sessions/{session_path:path}` | DELETE | Removes a session file via `session_manager.delete_session`. |
| `/api/v1/prompts` | GET | Lists available prompts, optionally filtered by `prompt_folder`. |
| `/api/v1/prompts/{prompt_path:path}` | GET | Reads specific prompt content via `prompt_manager.read_prompt`. |
| `/api/v1/model-configs` | GET | Scans `MODEL_CONFIG_DIR` for JSON files and returns model metadata. |
| `/api/v1/prompts` | POST | Creates a new prompt file via `prompt_manager.create_prompt`. |
| `/api/v1/prompts/{prompt_path:path}` | PUT | Updates existing prompt content via `prompt_manager.update_prompt`. |
| `/api/v1/prompts/{prompt_path:path}` | DELETE | Removes a prompt file via `prompt_manager.delete_prompt`. |
| `/api/v1/chat/completions` | POST | Handles chat requests (streaming/non-streaming) via `chat_service.chat_completion`. |
| `/api/v1/chat` | POST | Alias for chat completion endpoint. |
| `/api/health` | GET | Returns system status and current `brain_hub` model name. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Resolves `SESSION_ROOT_DIR` and `PROMPT_ROOT_DIR` using `func.get_root_directory()`.
    2. Instantiates `SessionManager`, `PromptManager`, and `ChatService`.
    3. Creates `FastAPI` instance.
    4. Checks for `FRONTEND_BUILD_DIR`; if present, mounts static files to `/`.
    5. Appends `MIOMETypeFixerMiddleware` and `CORSMiddleware`.
- **Data Path (Chat Completion)**: 
    `ChatCompletionRequest` (JSON) $\rightarrow$ `chat_service.chat_completion` $\rightarrow$ `BrainHub` processing $\rightarrow$ Streaming/JSON Response.
- **Data Path (Model Config Discovery)**: 
    `MODEL_CONFIG_DIR` $\rightarrow$ `rglob("*.json")` $\rightarrow$ `json.load` $\rightarrow$ List of `model_name` and `model_file` dicts.
- **Conditional Branching**:
    - **Static Files**: If `FRONTEND_BUILD_DIR.is_dir()` is true, mount the directory; otherwise, skip.
    - **Manager Availability**: Every endpoint checks if its respective manager (`session_manager`, `prompt_manager`, `chat_service`) is `None` before proceeding, raising a 500 error if unconfigured.
    - **Error Handling**: Specific catch blocks for `SessionNotFoundError`, `SessionInvalidPathError`, `PromptNotFoundError`, `PromptInvalidPathError`, and `PromptAccessError` to map internal exceptions to HTTP status codes (400, 404, 500).

## 4. Resource Dependencies
- **Standard Libraries**: `pathlib.Path`, `json`, `typing.Any`, `typing.Dict`, `typing.Optional`.
- **Internal Modules**: `functions` (as `func`), `.schemas`, `.middleware.MIMETypeFixerMiddleware`, `.services.session_manager`, `.services.prompt_manager`, `.services.chat`, `.brain_hub`.
- **External Packages**: `fastapi`, `fastapi.staticfiles`, `fastapi.middleware.cors`.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `SESSION_ROOT_DIR` path suffix: `/sessions/server`.
    - `PROMPT_ROOT_DIR` path suffix: `/system`.
    - `MODEL_CONFIG_DIR` path suffix: `/models`.
    - CORS `allow_origins`: `["*"]`.
- **Environment Lookups**: 
    - `func.get_root_directory()` (Used to anchor all filesystem-based pathing).