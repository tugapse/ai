## 1. Architectural Role
Acts as a network proxy that implements the `BaseModel` interface to delegate LLM inference and system control to a remote server via REST API.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `RemoteBrainConnector` | Class | Manages the connection, request dispatching, and response streaming from a remote inference backend. |
| `__init__` | Method | Initializes connection parameters (`url`, `model_id`) and sets the `inference_device` to `GPU_CUDA`. |
| `check_system_prompt` | Method | Pass-through validator for message structures. |
| `chat` | Method | Dispatches chat payloads to `/v1/chat/completions` and handles both synchronous and SSE (Server-Sent Events) streaming responses. |
| `request_shutdown` | Method | Signals the remote server to terminate via the `/v1/shutdown` endpoint. |
| `list` | Method | Queries the `/health` endpoint to retrieve the active remote model name. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `BaseModel` constructor.
    2. Strips trailing slashes from `url`.
    3. Assigns `model_id` and hardcodes `inference_device` to `InferenceBackend.GPU_CUDA`.
- **Data Path (Chat)**: 
    1. **Input**: Receives `messages`, `images`, `stream` flag, and `options`.
    2. **Payload Construction**: Wraps inputs into a JSON object including `temperature`, `system_prompt`, and `model_params`.
    3. **Transmission**: Executes a `requests.post` to the `/v1/chat/completions` endpoint.
    4. **Processing (Streaming)**: If `stream=True`, iterates over `response.iter_lines()`, strips `data: ` prefixes, parses JSON chunks, and yields `content` from the `delta` object.
    5. **Processing (Non-Streaming)**: If `stream=False`, parses the full JSON response and yields the `content` from the first choice.
    6. **Output**: Yields text strings (or error messages) to the caller.
- **Conditional Branching**:
    - **Stream vs. Non-Stream**: Determines whether to use `iter_lines()` for real-time chunks or `response.json()` for a single block.
    - **SSE Parsing**: Checks for `[DONE]` signal or `error` keys within the stream to terminate the generator.
    - **Type Validation**: In non-streaming mode, checks if `content` is a string or an empty list to provide fallback error text.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `requests`, `typing.Any`
- **Internal Modules**: `functions` (as `func`), `core.llms.base_llm.BaseModel`, `entities.model_enums.InferenceBackend`
- **External Packages**: `requests`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `endpoint` suffix: `/v1/chat/completions`
    - `shutdown` endpoint: `/v1/shutdown`
    - `health` endpoint: `/health`
    - `timeout`: 120 seconds (chat), 5 seconds (shutdown)
    - `default_temperature`: 0.7
    - `inference_device`: `InferenceBackend.GPU_CUDA`