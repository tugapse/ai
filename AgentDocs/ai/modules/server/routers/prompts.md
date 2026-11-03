## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Prompts Router** | [src/ai/modules/server/routers/prompts.py](/AgentDocs/ai/modules/server/routers/prompts.md) |

This component provides a FastAPI router that exposes a RESTful API for managing system prompts and model configurations. It serves as the interface between external clients and the internal prompt management logic, allowing for the retrieval, creation, updating, and deletion of prompt files stored on the filesystem.

As a controller within the server module, it orchestrates requests by delegating core business logic to the `prompt_manager` stored in the application state. It also provides an endpoint to discover available model configurations by scanning the models directory, facilitating dynamic model selection in the broader application architecture.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `get_prompts` | Function | `GET /api/v1/prompts`. Retrieves a list of saved prompts, optionally filtered by a sub-folder. |
| `get_prompt_content` | Function | `GET /api/v1/prompts/{prompt_path:path}`. Returns the raw content of a specific prompt file. |
| `get_model_configs` | Function | `GET /api/v1/model-configs`. Scans the models directory and returns a list of available model configurations. |
| `create_prompt` | Function | `POST /api/v1/prompts`. Creates a new prompt file using the provided path and content. |
| `update_prompt_content` | Function | `PUT /api/v1/prompts/{prompt_path:path}`. Overwrites the content of an existing prompt file. |
| `delete_prompt` | Function | `DELETE /api/v1/prompts/{prompt_path:path}`. Removes a specific prompt file from the system. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router acts as a thin wrapper around `prompt_manager` methods. For model configuration discovery, it performs a recursive glob search (`rglob`) for `.json` files within the `MODEL_CONFIG_DIR`, extracting the model name from the JSON content or defaulting to the filename.
- **Side Effects:** 
    - **Filesystem:** Performs extensive I/O operations including reading, writing, and deleting files within the prompt and model directories.
    - **State Access:** Relies on `request.app.state.prompt_manager` being initialized.
- **Error Handling:** 
    - Maps `PromptNotFoundError` to `404 Not Found`.
    - Maps `PromptInvalidPathError` to `400 Bad Request`.
    - Maps `PromptAccessError` to `500 Internal Server Error`.
    - Catches `json.JSONDecodeError` during model config loading to return a `500` error with specific file details.
    - Raises `500` errors if the `prompt_manager` is missing from the application state.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are accessed within this file; it relies on the root directory provided by [ai.functions](/AgentDocs/ai/functions.md).

**Module Dependencies:**
- **Standard/External:** `json`, `pathlib`, `typing`, `fastapi`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.modules.server.schemas](/AgentDocs/ai/modules/server/schemas.md)
    - [ai.modules.server.services.prompt_manager](/AgentDocs/ai/modules/server/services/prompt_manager.md)