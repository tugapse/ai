## 1. Architectural Role
Provides a unified interface for interacting with Google's Gemini models via either the Vertex AI enterprise platform or the Google GenAI SDK.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `GeminiAPIModel` | Class | Orchestrates model initialization, message conversion, image processing, and synchronous/streaming generation. |
| `__init__` | Method | Configures authentication, initializes the SDK/Vertex client, and maps model parameters. |
| `chat` | Method | Primary entry point for processing messages and images to generate a response. |
| `load_images` | Method | Converts image paths or objects into API-compatible byte parts. |
| `_convert_messages_to_api` | Method | Transforms internal message lists into `Content` objects required by the Google SDKs. |
| `_generate_response_sync` | Method | Executes a non-streaming request and extracts the final text or function call. |
| `_stream_generator` | Method | Executes a streaming request, yielding tokens or a function call. |
| `_extract_response_content` | Method | Parses API response objects to distinguish between text and `function_call` payloads. |
| `_check_gcp_auth` | Method | Validates Google Cloud authentication via environment variables or local config files. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Filters Vertex AI deprecation warnings.
    2. Checks `use_vertex` flag.
    3. If `use_vertex` is True: Validates GCP auth via `_check_gcp_auth`, initializes `vertexai` with `project_id` and `location`.
    4. If `use_vertex` is False: Initializes `google.genai.Client` using `api_key`.
    5. Maps `model_params` (temperature, max_new_tokens, top_p, top_k) to API-specific keys.
- **Data Path**: 
    `messages` + `images` $\rightarrow$ `_convert_messages_to_api` $\rightarrow$ `_append_images_to_history` $\rightarrow$ `chat` $\rightarrow$ (`_stream_generator` OR `_generate_response_sync`) $\rightarrow$ `_extract_response_content` $\rightarrow$ Final String or Function Call Dict.
- **Conditional Branching**:
    - **Auth Path**: Checks `GOOGLE_APPLICATION_CREDENTIALS` $\rightarrow$ Local JSON config $\rightarrow$ `gcloud` CLI check.
    - **Execution Mode**: `stream=True` triggers the generator; `stream=False` triggers the synchronous call.
    - **Response Type**: `_extract_response_content` branches based on whether the model returned a standard text response or a `function_call`.
    - **SDK Path**: Logic diverges throughout the class based on `self.use_vertex` to handle differences between `vertexai` and `google.genai` libraries.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `io`, `gc`, `time`, `re`, `subprocess`, `warnings`
- **Internal Modules**: `.base_llm` (`BaseModel`, `ModelParams`), `functions` (`func`), `color` (`Color`)
- **External Packages**: `vertexai` (optional), `google.genai` (optional), `PIL.Image` (optional)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default model: `"gemini-2.5-flash"`
    - Default location: `"us-central1"`
    - Default project: `"project-02da1a39-478c-49eb-a3e"`
- **Environment Lookups**: 
    - `GOOGLE_CLOUD_PROJECT`
    - `GEMINI_API_KEY`
    - `GOOGLE_JARVIS_API_KEY`
    - `GOOGLE_APPLICATION_CREDENTIALS`
    - `APPDATA` (Windows specific)