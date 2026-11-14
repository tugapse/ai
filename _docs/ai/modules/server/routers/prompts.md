## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| prompts | /ai/modules/server/routers/prompts.md |

This component serves as the API router responsible for managing all persistence and retrieval operations related to user-defined prompts within the application. It exposes endpoints for listing, creating, reading, updating, and deleting prompt files, providing a standardized interface for prompt interaction.

This router acts as the primary controller layer for prompt management, sitting between the external HTTP requests and the core business logic implemented in [ai.modules.server.services.prompt_manager](/ai/modules/server/services/prompt_manager.md). It relies on FastAPI for routing and handles request validation and error translation into appropriate HTTP responses.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| get_prompts | Function | Retrieves a list of saved prompts, optionally filtered by a sub-folder. |
| get_prompt_content | Function | Retrieves the content of a specific prompt file given its full path. |
| get_model_configs | Function | Lists all known model configurations managed by the server's BrainHub. |
| create_prompt | Function | Creates a new prompt file using the provided path and content. |
| update_prompt_content | Function | Overwrites the content of an existing prompt file at the specified path. |
| delete_prompt | Function | Deletes a specific prompt file identified by its path. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The router methods delegate persistence tasks to the `prompt_manager` instance, which is retrieved from the FastAPI application state. Each endpoint handles request parsing (path parameters, request body) and wraps the service calls in `try...except` blocks to translate specific service exceptions into standard HTTP error responses (e.g., `PromptNotFoundError` to 404).
- **Side Effects:** The component interacts heavily with the filesystem via the `prompt_manager` service (reading, writing, deleting files). It also relies on the application state to access the configured `prompt_manager` and `brain_hub`.
- **Error Handling:** Specific application exceptions (`PromptNotFoundError`, `PromptInvalidPathError`, `PromptAccessError`) are caught and mapped to appropriate HTTP status codes (404, 400, 500). A general `Exception` catch-all ensures a 500 response for unexpected failures.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `fastapi`, `typing`
- **Internal:** [ai.modules.server.routers.auth](/ai/modules/server/routers/auth.md), [ai.modules.server.schemas](/ai/modules/server/schemas.md), [ai.modules.server.services.prompt_manager](/ai/modules/server/services/prompt_manager.md)