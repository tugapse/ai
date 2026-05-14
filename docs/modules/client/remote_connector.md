## 1. Architectural Role
Acts as a network-based implementation of the `BaseModel` interface that proxies LLM inference requests to a remote API endpoint via HTTP.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `RemoteBrainConnector` | Class | Manages remote LLM connectivity, request payload construction, and response streaming/parsing. |
| `check_system_prompt` | Method | Validates or transforms the input message structure before transmission. |
| `chat` | Method | Executes the primary inference loop, supporting both synchronous JSON responses and asynchronous SSE streaming. |
| `request_shutdown` | Method | Signals the remote server to terminate via a POST request and manages local stop events. |
| `list` | Method | Performs a health check on the remote endpoint to retrieve available model identifiers. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__` to establish base model properties.
    2. Normalizes `url` by stripping trailing slashes.
    3. Sets `model_id` and defaults `inference_device` to `InferenceBackend.GPU_CUDA`.
- **Data Path**: 
    1. **Input**: `messages` (list), `images` (list), `stream` (bool), and `options` (dict).
    2. **Processing**: 
        - `messages` are passed through `check_system_prompt`.
        - A JSON `payload` is constructed containing `model`, `messages`, `stream`, `temperature`, `system_prompt`, and `model_params`.
        - An HTTP POST request is dispatched to `{url}/v1/chat/completions`.
    3. **Output**: A generator yielding string fragments (stream mode) or a single string (non-stream mode).
- **Conditional Branching**:
    - **Stream Mode (`stream=True`)**: 
        - Iterates through `response.iter_lines()`.
        - Filters for lines starting with `data: `.
        - Checks for `[DONE]` signal to break loop.
        - Parses JSON chunks to extract `choices[0].delta.content`.
        - Yields content or error messages.
    - **Non-Stream Mode (`stream=False`)**: 
        - Parses full JSON response.
        - Extracts `choices[0].message.content`.
        - Performs type validation/conversion on content.
        - Yields final string.
    - **Error Handling**: Catches exceptions during request or parsing to yield error strings prefixed with `[LINK ERROR: ...]` or `[Brain Error: ...]`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `requests`, `typing`
- **Internal Modules**: `functions` (as `func`), `core.llms.base_llm` (`BaseModel`), `entities.model_enums` (`InferenceBackend`)
- **External Packages**: `requests`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `InferenceBackend.GPU_CUDA` (Default device)
    - `/v1/chat/completions` (Chat endpoint)
    - `/v1/shutdown` (Shutdown endpoint)
    - `/health` (Health endpoint)
    - `120` (Request timeout in seconds)
    - `0.7` (Default temperature)
- **Environment Lookups**: None detected.