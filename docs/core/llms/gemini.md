## 1. Architectural Role
Provides a specialized implementation of `BaseModel` that interfaces with Google's Gemini API via either Vertex AI (Google Cloud) or the `google.genai` client, utilizing a "Pure Text Protocol" to flatten tool calls and results into text-based sequences for model processing.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `GeminiAPIModel` | Class | Manages the lifecycle, authentication, and communication with Gemini models. |
| `__init__` | Method | Configures model parameters, initializes Vertex AI or GenAI client, and sets up generation configs. |
| `_convert_messages_to_api` | Method | Transforms internal message history into Vertex AI `Content` objects, flattening tool calls/results into text. |
| `chat` | Method | Entry point for inference; handles system prompt injection, history conversion, and image appending. |
| `_stream_generator` | Method | Orchestrates asynchronous token streaming and intercepts sentinel tags for tool detection. |
| `_generate_response_sync` | Method | Executes synchronous, single-shot text generation. |
| `_check_gcp_auth` | Method | Validates Google Cloud authentication via environment variables, local JSON paths, or `gcloud` CLI. |
| `load_images` | Method | Converts raw image data or paths into `Part` objects compatible with Vertex AI. |
| `_append_images_to_history` | Method | Injects processed image parts into the most recent `user` role message in the history. |
| `is_gpu_available` | Method | Returns `False` (hardcoded). |
| `clean_cache` | Method | Triggers garbage collection. |

## 3. Execution Logic & Flow
- **Initialization**:
    1. Calls `super().__init__`.
    2. Determines authentication mode (`use_vertex`).
    3. If `use_vertex`: Validates GCP credentials via `_check_gcp_auth`, initializes `vertexai`, and maps `GenerationConfig` and `Part` classes.
    4. If not `use_vertex`: Initializes `genai.Client` using the provided `api_key` or `GEMINI_API_KEY`.
    5. Maps `model_params` (temperature, top_p, etc.) to `self.config_kwargs`.
- **Data Path**:
    1. **Input**: `messages` (list of dicts), `images` (list), `stream` (bool), `options` (dict).
    2. **Preprocessing**:
        - Extracts/constructs `dynamic_system_prompt`.
        - `_convert_messages_to_api` transforms roles: `tool`/`function` $\rightarrow$ `user` text; `assistant` + `tool_calls` $\rightarrow$ `model` text; consecutive roles $\rightarrow$ merged `parts`.
        - `_append_images_to_history` attaches image `Part` objects to the last `user` message.
    3. **Processing**:
        - `model.generate_content` is called with the processed history and configuration.
        - In streaming mode, the generator iterates through response chunks.
        - `handle_sentinel` intercepts specific text patterns to detect function calls.
    4. **Output**: Yields/returns text strings or parsed dictionary objects (for tool calls).
- **Conditional Branching**:
    - **Auth Path**: `use_vertex` determines whether to use `vertexai` or `google.genai`.
    - **Inference Path**: `stream=True` triggers `_stream_generator`; `stream=False` triggers `_generate_response_sync`.
    - **Role Flattening**: `_convert_messages_to_api` branches logic based on whether a message role is `system`, `tool`, `function`, `assistant`, or `user`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `io`, `gc`, `time`, `re`, `subprocess`, `warnings`, `json`.
- **Internal Modules**: `.base_llm` (`BaseModel`, `ModelParams`), `functions` (`func`), `color` (`Color`).
- **External Packages**: `vertexai` (`GenerativeModel`, `Part`, `GenerationConfig`, `Content`), `google.genai` (`Client`), `PIL.Image`.

## 5. Configuration & Environment
- **Hardcoded Constants**:
    - `model_name` default: `"gemini-2.5-flash"`.
    - `use_vertex` default: `True`.
    - `CONTEXT_WINDO_1M` (referenced via `self.token_info_count`).
- **Environment Lookups**:
    - `GOOGLE_CLOUD_PROJECT`
    - `GEMINI_API_KEY`
    - `GOOGLE_APPLICATION_CREDENTIALS`
    - `APPDATA` (for Windows pathing)