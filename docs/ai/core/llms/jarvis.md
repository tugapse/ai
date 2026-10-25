## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | JarvisAiModel |
| Source file | jarvis.py |

The **JarvisAiModel** serves as a specialized client-side interface designed to bridge the local application logic with a custom FastAPI-based backend. It acts as a high-level abstraction layer that translates standard LLM interaction patterns into specific HTTP requests compatible with the JARVIS custom endpoint, ensuring that the rest of the system can interact with a remote backend as if it were a local model.

**Functional Mission**
The primary responsibility of **JarvisAiModel** is to facilitate seamless communication with a remote inference server while maintaining strict protocol compatibility with the [BaseModel](/docs/ai/core/llms/base_llm.md). It solves the problem of heterogeneous backend integration by encapsulating session management, streaming logic, and error handling within a standardized class structure, allowing the [Model Orchestrator](/docs/ai/services/model_orchestrator.md) to treat the remote service as a native component.

**System Context & Integration**
This component sits at the edge of the LLM abstraction layer. It receives high-level chat requests from the [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md) or [LLM Connector](/docs/ai/agents/llm_connector.md) and converts them into JSON payloads. It manages the lifecycle of a request through both synchronous and streaming modes, emitting events via the [BaseModel](/docs/ai/core/llms/base_llm.md) event system to signal token generation or completion. This ensures that downstream components like the [Stream Orchestrator](/docs/ai/services/stream_orchestrator.md) can react to real-time data arrival.

- **INTERNAL REFERENCES**: [BaseModel](/docs/ai/core/llms/base_llm.md), [Model Orchestrator](/docs/ai/services/model_orchestrator.md), [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md), [LLM Connector](/docs/ai/agents/llm_connector.md), [Stream Orchestrator](/docs/ai/services/stream_orchestrator.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `AI_MODEL_NAME` (via `__init__`)  Determines the default model identifier if not provided.
- `AI_API_BASE_URL` (via `__init__`)  Defines the root URL for the custom FastAPI backend.

**Hardcoded Constants:**
- `gpt-4o` (Default: `model_name`)  Fallback model name.
- `http://0.0.0.0:9999` (Default: `base_url`)  Fallback backend endpoint.
- `600.0` (Default: `time_out`)  Default timeout duration in seconds for HTTP requests.
- `2048` (Default: `out_tokens`)  Default maximum new tokens if not specified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `JarvisAiModel` | Class | The main interface for interacting with the JARVIS custom backend. |
| `__init__` | Method | Configures API endpoints, session IDs, and token constraints. |
| `chat` | Method | The primary entry point for sending messages; supports both streaming and non-streaming modes. |
| `_run_streaming_chat` | Method | Internal generator that parses SSE (Server-Sent Events) from the backend. |
| `clean_cache` | Method | Triggers manual garbage collection to manage memory. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Resolves `model_name` and `base_url` from arguments or environment variables.
    2. Constructs the full API endpoint path.
    3. Sets up session-specific metadata (`session_id`, `session_folder`).
    4. Configures token limits and timeout settings.
- **Data Path**:
    1. **Input**: A list of message dictionaries and optional image data.
    2. **Processing**: 
        - Synchronizes the `system_prompt` by checking the message history.
        - Constructs a JSON payload including model info, session context, and messages.
        - Dispatches an HTTP POST request via `httpx`.
    3. **Output**: 
        - *Non-streaming*: Returns the final string content.
        - *Streaming*: Yields individual content chunks as they arrive from the server.
- **Conditional Branching**:
    - **Stream Toggle**: If `stream=True`, routes to `_run_streaming_chat`; otherwise, performs a standard blocking POST.
    - **System Prompt Check**: If no 'system' role is found in the input messages, it injects the class's `system_prompt` at index 0.
    - **Error Handling**: Catches exceptions during network I/O, logs them via `func.error`, and triggers the `STREAMING_FINISHED_EVENT` to prevent downstream hangs.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `gc`, `json`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
- **External Packages**: `httpx`