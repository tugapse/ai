## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **JarvisAiModel** | [src/ai/core/llms/jarvis.py](/src/ai/core/llms/jarvis.py) |

The `JarvisAiModel` serves as a specialized client interface designed to communicate with a custom FastAPI backend endpoint. It is engineered to maintain structural parity with existing Orchestrator and Sentinel protocols, ensuring that the custom backend can be swapped in as a drop-in replacement for other LLM providers without breaking the higher-level agent logic.

This component acts as a bridge between the core AI orchestration layer and a remote inference server. It handles the complexities of session management (via `session_id` and `session_folder`), manages streaming data parsing from custom SSE-like (Server-Sent Events) formats, and synchronizes system prompts dynamically during the chat lifecycle.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `JarvisAiModel(...)` | Class | Initializes the interface with model configuration, backend URL, and session state. Inherits from [BaseModel](/AgentDocs/ai/core/llms/base_llm.md). |
| `chat(messages, images, stream, options)` | Method | Executes a chat completion request. Supports both blocking text returns and asynchronous generators for streaming. |
| `clean_cache()` | Method | Triggers manual garbage collection to release memory buffers. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Prompt Management:** The `chat` method inspects the message history for a `system` role. If found, it updates the internal `system_prompt`; otherwise, it injects the class's `system_prompt` at the start of the message list.
    - **Streaming Protocol:** The `_run_streaming_chat` method implements a custom parser for the backend's stream. It expects lines prefixed with `data: `, strips the prefix, and parses the remaining JSON. It specifically looks for `choices[0].delta.content` and handles the `[DONE]` termination signal.
    - **Token Tracking:** Updates `token_info_count` attributes based on provided `max_new_tokens` and `n_ctx` arguments.
- **Side Effects:** 
    - **Network I/O:** Performs synchronous or streaming HTTP POST requests to a remote endpoint via `httpx`.
    - **Event Signaling:** Triggers internal events such as `"token"` (emitted per chunk) and `BaseModel.STREAMING_FINISHED_EVENT` (emitted upon completion or error).
    - **Logging:** Uses [func.log](/AgentDocs/ai/functions.md) and [func.error](/AgentDocs/ai/functions.md) to report connection status and runtime exceptions.
- **Error Handling:** 
    - Catches `httpx` request errors and `json.JSONDecodeError`.
    - In the event of a failure during chat or streaming, it logs the error, triggers the `STREAMING_FINISHED_EVENT`, and returns an empty string to prevent total system collapse.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_MODEL_NAME`  Sets the default LLM model name if not provided (defaults to `gpt-4o`).
- `AI_API_BASE_URL`  Sets the base URL for the custom FastAPI backend (defaults to `http://0.0.0.0:9999`).

**Module Dependencies:**
- **Standard/External:** `os`, `gc`, `json`, `typing`, `httpx`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.core.llms.base_llm.BaseModel](/AgentDocs/ai/core/llms/base_llm.md)