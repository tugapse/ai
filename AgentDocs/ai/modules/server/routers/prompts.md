## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Prompts Router** | [src/ai/modules/server/routers/prompts.py](/src/ai/modules/server/routers/prompts.py) |

The Prompts Router provides a RESTful API interface for managing prompt templates and model configurations. It acts as the controller layer for prompt-related operations, allowing users to list, retrieve, create, update, and delete prompt files stored on the filesystem.

This component is part of the server module architecture, serving as the bridge between external HTTP requests and the internal [prompt_manager](/ai/modules/server/services/prompt_manager.md) service. It also provides an endpoint to discover available model configurations within the system's model directory.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `get_prompts` | Function | `GET /api/v1/prompts`. Retrieves a list of saved prompts, optionally filtered by a `prompt_folder` query parameter. |
| `get_prompt_content` | Function | `GET /api/v1/prompts/{prompt_path:path}`. Returns the raw content of a specific prompt file identified by its path. |
| `get_model_configs` | Function | `GET /api/v1/model-configs`. Scans the `models` directory for `.json` files and returns a list of model names and their relative file paths. |
| `create_prompt` | Function | `POST /api/v1/prompts`. Creates a new prompt file using the provided `PromptCreateRequest` payload. |
| `update_prompt_content` | Function | `PUT /api/v1/prompts/{prompt_path:path}`. Overwrites the content of an existing prompt file using a `PromptUpdateRequest` payload. |
| `delete_prompt` | Function | `DELETE /api/v1/prompts/{prompt_path:path}`. Removes a specific prompt file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router relies heavily on the `prompt_manager` instance attached to the FastAPI `app.state`. Most operations are pass-through calls to this manager. For model configurations, the router performs a recursive glob search (`rglob`) for `.json` files within the `models` directory relative to the application root.
- **Side Effects:** 
    - **Filesystem:** Performs extensive I/O operations, including reading, writing, and deleting files in the prompt storage directory and the model configuration directory.
    - **Network:** Responds to HTTP requests via the FastAPI framework.
- **Error Handling:** 
    - Maps internal service exceptions to standard HTTP status codes:
        - `PromptNotFoundError` $\rightarrow$ `404 Not Found`
        - `PromptInvalidPathError` $\rightarrow$ `400 Bad Request`
        - `PromptAccessError` $\rightarrow$ `500 Internal Server Error`
    - Throws `500 Internal Server Error` if the `prompt_manager` is missing from the application state or if unexpected filesystem/JSON errors occur.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are directly accessed in this file; however, the location of the `models` directory is determined by the root directory provided by [func.get_root_directory()](/ai/functions.md).

**Module Dependencies:**
- **Standard/External:** `json`, `pathlib`, `typing`, `fastapi`.
- **Internal:**
    - [ai.functions](/ai/functions.md)
    - [ai.modules.server.schemas](/ai/modules/server/schemas.md)
    - [ai.modules.server.services.prompt_manager](/ai/modules/server/services/prompt_manager.md)