## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Prompts Router |
| Source file | prompts.py |

The **prompts.py** component serves as the RESTful API interface layer for managing prompt templates and model configurations within the server module. It acts as a specialized controller that exposes HTTP endpoints to perform CRUD (Create, Read, Update, Delete) operations on prompt files stored on the filesystem, abstracting the underlying file I/O through a dedicated service layer.

**Functional Mission**
The primary mission of the **prompts.py** router is to provide a standardized web interface for prompt lifecycle management. It solves the problem of programmatic access to prompt assets, allowing external clients or frontend interfaces to list, retrieve, create, modify, and delete prompt templates and inspect available model configurations without direct filesystem access.

**System Context & Integration**
This component sits within the web server layer, receiving HTTP requests and delegating the core business logic to the `prompt_manager` instance attached to the FastAPI application state. It acts as a bridge between the network layer and the [Prompt Manager](/docs/ai/modules/server/services/prompt_manager.md). When a request is received, it validates the input against [Prompt Schemas](/docs/ai/modules/server/schemas.md) and translates service-layer exceptions (such as `PromptNotFoundError`) into appropriate HTTP status codes. Additionally, it provides visibility into the `models` directory by parsing JSON configurations, facilitating the synchronization between available model files and the application's configuration state.

- **INTERNAL REFERENCES**: 
    - [Prompt Manager](/docs/ai/modules/server/services/prompt_manager.md)
    - [Prompt Schemas](/docs/ai/modules/server/schemas.md)
    - [Functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `func.get_root_directory()`  Used to resolve the absolute base path for the `models` directory and prompt storage.

**Hardcoded Constants:**
- `MODEL_CONFIG_DIR` (Default: `Path(func.get_root_directory()) / "models"`)  The filesystem path where model configuration JSON files are located.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `get_prompts` | Async Func | Retrieves a list of prompt files, optionally filtered by a sub-folder. |
| `get_prompt_content` | Async Func | Fetches the raw text content of a specific prompt file via its path. |
| `get_model_configs` | Async Func | Scans the model directory and returns a list of available model metadata. |
| `create_prompt` | Async Func | Persists a new prompt file to the filesystem using provided content. |
| `update_prompt_content` | Async Func | Overwrites the content of an existing prompt file. |
| `delete_prompt` | Async Func | Removes a prompt file from the filesystem. |

## 4. Execution Logic & Flow
- **Initialization**: The router is instantiated via `APIRouter()`. It relies on the `request.app.state.prompt_manager` being pre-configured during the application startup sequence.
- **Data Path**:
    1. **Input**: HTTP Request (Method, Path, Query Params, or JSON Body).
    2. **Validation**: FastAPI validates the payload against [Prompt Schemas](/docs/ai/modules/server/schemas.md).
    3. **Delegation**: The router calls the corresponding method on the `prompt_manager`.
    4. **Processing**: The `prompt_manager` performs filesystem operations.
    5. **Output**: The router returns a JSON response or raises an `HTTPException`.
- **Conditional Branching**:
    - **Manager Check**: Every endpoint first verifies if `prompt_manager` is present in `app.state`; if not, it returns a `500 Internal Server Error`.
    - **Error Mapping**: 
        - `PromptNotFoundError` $\rightarrow$ `404 Not Found`.
        - `PromptInvalidPathError` $\rightarrow$ `400 Bad Request`.
        - `PromptAccessError` $\rightarrow$ `500 Internal Server Error`.
        - Generic `Exception` $\rightarrow$ `500 Internal Server Error`.
    - **Model Config Scan**: `get_model_configs` checks for directory existence and handles `json.JSONDecodeError` if a config file is malformed.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `pathlib.Path`, `typing.Optional`
- **Internal Modules**: 
    - [Functions](/docs/ai/functions.md)
    - [Prompt Schemas](/docs/ai/modules/server/schemas.md)
    - [Prompt Manager](/docs/ai/modules/server/services/prompt_manager.md)
- **External Packages**: `fastapi`