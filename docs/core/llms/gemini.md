## 1. Architectural Role
`GeminiAPIModel` serves as the specialized implementation for interacting with Google's Gemini ecosystem, supporting both Vertex AI (via Google Cloud Platform) and the standard Google GenAI API. It acts as a translation layer that converts high-level message structures into the specific requirements of the Vertex AI API, specifically handling the flattening of tool calls and results into a "Pure Text Protocol" to maintain compatibility with the orchestrator's manual tag system. It inherits core LLM capabilities from [base_llm](src/ai/core/llms/base_llm.md) and manages multimodal inputs (images) and streaming responses with sentinel interception.

## 2. Environment & Configuration
**Environment Lookups:**
- `GOOGLE_CLOUD_PROJECT` (via `__init__`)  Identifies the GCP project for Vertex AI initialization.
- `GEMINI_API_KEY` (via `__init__`)  Authentication key for the non-Vertex GenAI client.
- `GOOGLE_APPLICATION_CREDENTIALS` (via `_check_gcp_auth`)  Path to GCP service account credentials.

**Hardcoded Constants:**
- `CONTEXT_WINDO_1M` (via `__init__`)  Default context window limit (inherited).
- `us-central1` (via `__init__`)  Default Vertex AI location.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `GeminiAPIModel` | Class | Primary interface for Gemini/Vertex AI model interaction. |
| `chat` | Method | Entry point for generating responses; handles history conversion and multimodal injection. |
| `_convert_messages_to_api` | Method | Transforms orchestration messages (including tool/function roles) into Vertex-compatible `Content`/`Part` structures. |
| `_stream_generator` | Method | Manages real-time token streaming and intercepts manual sentinel tags for tool detection. |
| `_generate_response_sync` | Method | Executes a blocking single-shot generation request. |
| `_check_gcp_auth` | Method | Validates Google Cloud authentication via environment or `gcloud` CLI. |
| `load_images` | Method | Converts image paths or PIL objects into Vertex AI `Part` byte data. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Validates GCP credentials if `use_vertex` is enabled.
    2. Initializes `vertexai` or `google.genai` client.
    3. Maps configuration parameters (`temperature`, `max_new_tokens`, etc.) to API-specific keys.
- **Data Path**: 
    1. **Input**: `messages` (list of dicts) + `images` (list).
    2. **Preprocessing**: `_convert_messages_to_api` flattens tool calls into text tags (e.g., `____@tool call:...`) and merges consecutive roles to satisfy Vertex AI's strict alternating role requirement.
    3. **Multimodal Injection**: `_append_images_to_history` attaches image `Part` objects to the last `user` message.
    4. **Generation**: Sends structured `history` to the model via `generate_content`.
    5. **Interception**: In stream mode, the `handle_sentinel` method (inherited) monitors text for specific patterns to trigger tool calls.
    6. **Output**: Yields tokens (stream) or returns final text/parsed actions (sync).
- **Conditional Branching**:
    - `use_vertex` (bool): Determines if the model uses Vertex AI SDK or Google GenAI SDK.
    - `stream` (bool): Toggles between `_stream_generator` and `_generate_response_sync`.
    - `role == 'tool'`: Flattens results into a `user` role message to bypass API restrictions.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `io`, `gc`, `time`, `re`, `subprocess`, `warnings`, `json`
- **Internal Modules**: 
    - [base_llm](src/ai/core/llms/base_llm.md)
    - [functions](functions.md)
    - [color](color.md)
- **External Packages**: `vertexai` (google-cloud-aiplatform), `google.genai`, `PIL` (Pillow)