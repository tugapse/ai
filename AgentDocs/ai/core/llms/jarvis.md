## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **JarvisAiModel** | [src/ai/core/llms/jarvis.py](/AgentDocs/ai/core/llms/jarvis.md) |

The `JarvisAiModel` class serves as a specialized client interface designed to communicate with a custom FastAPI backend endpoint. It is engineered to maintain structural parity with existing Orchestrator and Sentinel protocols, ensuring that the custom backend can be swapped in as a drop-in replacement for other LLM providers without breaking system-wide event signaling.

Within the broader application architecture, this component acts as a high-level LLM driver. It abstracts the complexities of HTTP communication, streaming response parsing, and session management, providing a standardized interface that conforms to the [BaseModel](/AgentDocs/ai/core/llms/base_llm.md) specification used throughout the AI core.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `JarvisAiModel(...)` | Class | Initializes the interface with model name, system prompt, and backend configuration (base URL, session IDs). |
| `chat(messages, images, stream, options)` | Method | Executes a chat completion request. Returns a string (non-streaming), a dictionary, or a generator (streaming). |
| `clean_cache()` | Method | Triggers manual garbage collection to clear memory buffers. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class manages the construction of a `ChatCompletionRequest` payload, including `system_prompt_content`, `session_id`, and `session_folder`. For streaming requests, it implements a line-by-line parser that strips the `data: ` prefix from the FastAPI stream, handles the `[DONE]` sentinel value, and extracts content from the JSON delta chunks. It also performs dynamic system prompt injection by scanning the message history for a `system` role.
- **Side Effects:** 
    - **Network:** Performs synchronous or streaming HTTP POST requests to a remote endpoint via `httpx`.
    - **State/Events:** Triggers `token` events for every content chunk received and signals `STREAMING_FINISHED_EVENT` upon completion or error.
    - **Memory:** Interacts with the Python garbage collector via `gc.collect()`.
- **Error Handling:** Catches exceptions during both standard and streaming requests. In the event of a failure, it logs the error via [func.error](/AgentDocs/ai/functions.md), triggers the `STREAMING_FINISHED_EVENT` to prevent system hangs, and returns an empty string.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_MODEL_NAME`  Defines the default LLM model name if not provided (defaults to `gpt-4o`).
- `AI_API_BASE_URL`  Defines the base URL for the custom FastAPI backend (defaults to `http://0.0.0.0:9999`).

**Module Dependencies:**
- **Standard/External:** `os`, `gc`, `json`, `typing`, `httpx`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)