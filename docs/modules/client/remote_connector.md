## 1. Architectural Role
`RemoteBrainConnector` acts as the network abstraction layer facilitating communication between the local client (Tiny PC) and a remote inference server (Main PC). It implements the [base_llm.md](core/llms/base_llm.md) interface, translating local model calls into HTTP/REST requests. It manages both synchronous and asynchronous (SSE) streaming responses, handling the serialization of chat messages and the deserialization of server-side deltas to provide a seamless unified interface for LLM interaction regardless of physical hardware location.

## 2. Environment & Configuration
**Environment Lookups:**
- `url` (via `__init__`)  The base endpoint for the remote API.
- `model_id` (via `__init__`)  Identifier for the specific model hosted on the remote server.

**Hardcoded Constants:**
- `inference_device` (Default: `InferenceBackend.GPU_CUDA`)  Sets the assumed backend for the remote model.
- `timeout` (Default: `120`)  Maximum seconds to wait for the HTTP request/stream.
- `endpoint` (Default: `/api/v1/chat/completions`)  The specific API route for chat completions.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `RemoteBrainConnector` | Class | Orchestrates remote API communication via HTTP. |
| `check_system_prompt` | Method | Validates/passes through message structures before transmission. |
| `chat` | Method | Primary execution entry point; handles streaming vs. non-streaming logic and yields content. |
| `request_shutdown` | Method | Triggers a remote shutdown sequence for the host server. |
| `list` | Method | Performs a health check to retrieve the currently active remote model name. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up the remote URL, model identifier, and hardcodes the inference backend to CUDA.
- **Data Path**: 
    - **Input**: `messages` (list), `images` (list), `stream` (bool), `options` (dict).
    - **Processing**: 
        1. Constructs a JSON payload including `model`, `messages`, `stream`, and `model_params`.
        2. Dispatches an HTTP POST request via `requests`.
        3. **If `stream=True`**: Iterates through `response.iter_lines()`, strips the `data: ` prefix, parses JSON chunks, and yields `delta.content`.
        4. **If `stream=False`**: Parses the full JSON response and yields `choices[0].message.content`.
    - **Output**: A generator yielding strings (text chunks or error messages).
- **Conditional Branching**:
    - **Stream vs. Block**: Divergent logic paths based on the `stream` boolean to handle SSE vs. standard JSON.
    - **Error Handling**: Traps `json.JSONDecodeError` during stream parsing and general `Exception` to yield readable error strings instead of crashing.
    - **Empty Content Check**: Validates content type/length in non-streaming mode to handle null/empty server responses.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: 
    - [base_llm.md](core/llms/base_llm.md)
    - [model_enums.md](entities/model_enums.md)
    - [functions.md](functions.md)
- **External Packages**: `requests`