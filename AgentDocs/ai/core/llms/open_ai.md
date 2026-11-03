## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **OpenAIAPIModel** | [src/ai/core/llms/open_ai.py](/AgentDocs/ai/core/llms/open_ai.md) |

The `OpenAIAPIModel` class provides a generalized, OpenAI-compatible interface designed for the Just A Reasoning Virtual Intelligent Sentinel (JARVIS) system. It abstracts the complexities of interacting with various providers that adhere to the OpenAI specification, including OpenAI, Azure AI Foundry, Mistral, Ollama, and vLLM.

Its primary responsibility is to manage standard text generation and real-time telemetry while enforcing a strict "Sentinel Protocol." Rather than relying on native API tool-calling mechanisms, this component flattens tool calls and results into pure text-based protocols (e.g., `, `____@tool call:...`). This ensures that the model remains provider-agnostic and that tool interception is handled consistently by the internal Sentinel logic.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `OpenAIAPIModel` | Class | The primary interface for interacting with OpenAI-compatible LLMs. Inherits from [BaseModel](/AgentDocs/ai/core/llms/base_llm.md). |
| `chat()` | Method | Executes a chat completion request. Supports both synchronous text returns and asynchronous streaming via a Generator. Bypasses native tool-calling to enforce text-based protocol. |
| `clean_cache()` | Method | Forces a garbage collection cycle to clear internal memory buffers. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Message Conversion:** The `_convert_messages` method transforms internal message history into the OpenAI schema. It specifically flattens `tool` and `function` roles into `user` messages and converts `assistant` tool calls into a specialized text string (`____@tool call:...`) to maintain protocol consistency.
    - **Dynamic Parameterization:** The class detects "reasoning" models (e.g., `o1`, `nano`) via keyword matching in the model name to switch between `max_tokens` and `max_completion_tokens` parameters.
    - **Sentinel Interception:** During streaming, the `_run_streaming_chat` method monitors incoming chunks for specific text patterns. If a tool call is detected via the Sentinel protocol, it intercepts the stream and yields a tool action dictionary instead of raw text.
- **Side Effects:** 
    - **Network I/O:** Performs synchronous or streaming HTTP requests to external LLM API endpoints.
    - **Telemetry:** Updates internal token usage metrics (`token_info_count`) and triggers system events (e.g., `token`, `tool_detected`, `STREAMING_FINISHED_EVENT`).
    - **Logging:** Utilizes [func](/AgentDocs/ai/functions.md) for error and status logging.
- **Error Handling:** 
    - Raises `ImportError` if the `openai` package is missing.
    - Catches API exceptions during chat and stream execution, logging them via `func.error` and triggering the `STREAMING_FINISHED_EVENT` to prevent system hangs.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_MODEL_NAME`  Defines the model or Azure deployment name. Defaults to `gpt-4o`.
- `AI_API_KEY`  The authentication key for the LLM provider.
- `AI_API_VERSION`  The specific API version for Azure deployments.
- `AI_AZURE_ENDPOINT`  The endpoint URL for Azure-specific routing.

**Module Dependencies:**
- **Standard/External:** `os`, `threading`, `gc`, `json`, `typing`, `openai` (required).
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.tools.tool_registry](/AgentDocs/ai/tools/tool_registry.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.color](/AgentDocs/ai/color.md)