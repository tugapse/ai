## 1. Architectural Role

**Functional Mission**
The **RemoteBrainConnector** serves as a specialized network bridge designed to extend the system's intelligence capabilities by offloading inference tasks to a remote host. Its primary mission is to implement the standard LLM interface while abstracting the complexities of HTTP-based communication, specifically handling the translation of local model calls into remote API requests via a structured JSON payload.

**System Context & Integration**
This component acts as a remote implementation of the [BaseModel](/docs/core/llms/base_llm.md) interface, allowing the local system to treat a remote server as if it were a local inference engine. It integrates into the execution flow by intercepting chat requests and managing the lifecycle of streaming or non-streaming responses. It is critical for distributed architectures where the "Tiny PC" (client) lacks the hardware resources for local inference and must rely on a "Main PC" (server) for heavy computation.

## 2. Environment & Configuration

**Environment Lookups:**
- `url` (via `__init__`)  The base endpoint for the remote API.
- `model_id` (via `__init__`)  The specific identifier for the remote model to be invoked.

**Hardcoded Constants:**
- `inference_device` (Default: `InferenceBackend.GPU_CUDA`)  Hardcoded assumption of remote hardware capability.
- `timeout` (Default: `120`)  Maximum duration for the POST request.
- `temperature` (Default: `0.7`)  Default sampling temperature if not provided in `options`.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `RemoteBrainConnector` | Class | Orchestrates remote API communication following the `BaseModel` contract. |
| `check_system_prompt` | Method | Validates or transforms the message structure before transmission. |
| `chat` | Method | The primary execution engine; handles both streaming (SSE) and standard JSON request/response cycles. |
| `request_shutdown` | Method | Sends a termination signal to the remote host and manages local event state. |
| `list` | Method | Performs a health check and retrieves the available model name from the remote endpoint. |

## 4. Execution Logic & Flow

- **Initialization**: Sets the remote `url`, `model_id`, and configures the `inference_device` to `GPU_CUDA`. It inherits base properties from `BaseModel`.
- **Data Path**: 
    1. **Input**: Receives `messages` (list), `images` (list), `stream` (bool), and `options` (dict).
    2. **Processing**: Constructs a JSON payload containing the model ID, messages, temperature, system prompt, and model parameters.
    3. **Transmission**: Dispatches a `requests.post` to the `/api/v1/chat/completions` endpoint.
    4. **Output**: 
        - *If `stream=True`*: Iterates through SSE lines, strips the `data: ` prefix, parses JSON chunks, and `yields` content deltas.
        - *If `stream=False`*: Parses the full JSON response and `yields` the complete message content.
- **Conditional Branching**:
    - **Stream Mode**: Checks for `[DONE]` signals and handles `error` keys within the JSON stream.
    - **Non-Stream Mode**: Validates the existence of `choices` and performs type-checking/casting on the content to ensure a string is returned.
    - **Error Handling**: Catches connection or parsing exceptions and yields a formatted error string (e.g., `[LINK ERROR: ...]`).

## 5. Resource Dependencies

- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [InferenceBackend](/docs/entities/model_enums.md)
- **External Packages**: `requests`