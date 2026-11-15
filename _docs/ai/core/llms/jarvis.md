## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| JarvisAiModel | ai/core/llms/jarvis.md |

This component provides a specialized client interface, `JarvisAiModel`, designed to interact specifically with a custom, proprietary FastAPI backend endpoint designated as the "JARVIS" service. Its primary responsibility is to abstract the underlying HTTP communication, allowing higher-level components to treat the custom backend as a standard LLM provider, ensuring seamless integration with existing orchestration and sentinel protocols.

This class acts as a specialized service wrapper within the application architecture. It bridges the gap between the standard `BaseModel` contract and the unique requirements of the custom backend, handling configuration routing (like `base_url` and `server_model`), session management, and the complexities of synchronous vs. streaming API calls.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `JarvisAiModel` | Class | A drop-in client interface tailored for the JARVIS custom FastAPI endpoint. |
| `JarvisAiModel.chat` | Method | Executes a chat completion request directly to the custom backend endpoint, supporting streaming or synchronous return. |
| `JarvisAiModel.clean_cache` | Method | Forces garbage collection to clear memory buffers associated with the model instance. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class initializes by setting up connection parameters based on environment variables or provided arguments, routing traffic to a specific endpoint. The `chat` method constructs a payload targeting the backend's chat completion schema. It delegates execution to either `_run_sync_chat` (for blocking calls) or `_run_streaming_chat` (for yielding chunks). Streaming utilizes `stream_with_retry` to manage connection reliability while yielding content chunks from SSE lines.
- **Side Effects:** Interacts heavily with the network via `httpx` to communicate with the external custom backend endpoint. It also mutates internal state related to token tracking and triggers events via `self.trigger()`.
- **Error Handling:** It implements robust retry logic via `RetryPolicy` for network failures (timeouts, 5xx errors). Specific HTTP status errors are captured by `_raise_for_status`, which attempts to extract detailed error messages from the server's response body. Exceptions are wrapped and surfaced as `LLMAPIError` to the caller.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_MODEL_NAME` — Used as a fallback for the default model name if not explicitly provided during initialization.
- `AI_API_BASE_URL` — Defines the base URL for the custom backend API endpoint if not specified during initialization.
- `AI_SERVER_MODEL` — Defines the specific model configuration file name the server should load if not specified during initialization.

**Module Dependencies:**
- **Standard/External:** `os`, `gc`, `json`, `typing`, `httpx`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.core.llms.api_retry.LLMAPIError](/ai/core/llms/api_retry.md), [ai.core.llms.api_retry.RetryPolicy](/ai/core/llms/api_retry.md), [ai.core.llms.api_retry.call_with_retry](/ai/core/llms/api_retry.md), [ai.core.llms.api_retry.stream_with_retry](/ai/core/llms/api_retry.md), [ai.core.llms.base_llm.BaseModel](/ai/core/llms/base_llm.md).