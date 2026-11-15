## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| OpenAIAPIModel | /ai/core/llms/open_ai.md |

This component provides a generalized, OpenAI-compatible interface for interacting with various large language model providers (including OpenAI and Azure AI Foundry). Its primary responsibility is to abstract the underlying API calls, ensuring that the core application logic interacts with a consistent, protocol-agnostic interface, even when dealing with provider-specific nuances. It specifically enforces a "Sentinel Protocol" by flattening complex native tool calls into pure text markers (` (`____@tool call:...`) to allow for consistent interception by the application's reasoning layer.

This class functions as a critical service layer within the architecture, sitting between the high-level reasoning engine and the external LLM APIs. It integrates configuration management (API keys, endpoints), implements robust retry logic via [ai.core.llms.api_retry.RetryPolicy](/ai/core/llms/api_retry.md), and manages telemetry tracking by updating internal metrics via [ai.core.llms.base_llm.BaseModel](/ai/core/llms/base_llm.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `OpenAIAPIModel` | Class | A generalized, OpenAI-compatible API interface for JARVIS. Handles text generation, streaming, and tool call interception. |
| `chat` | Method | Executes a chat completion request. Returns final text, a detected tool action dictionary, or a generator for streaming responses. |
| `clean_cache` | Method | Forces garbage collection to clear memory buffers used by the instance. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `chat` method first transforms the internal message history into the standard OpenAI schema using `_convert_messages`, which flattens tool results and calls into specific text markers. It then uses `call_with_retry` or `stream_with_retry` to communicate with the configured client (OpenAI or Azure). Streaming responses are processed chunk-by-chunk through `_run_streaming_chat`, where the `handle_sentinel` method intercepts custom text protocols to detect and yield structured tool actions before they reach the caller.
- **Side Effects:** Interacts heavily with external network services (OpenAI/Azure APIs). Mutates internal state related to token tracking via `_update_token_metrics`.
- **Error Handling:** Catches `LLMAPIError` and general exceptions during API calls. Errors are wrapped using `wrap_error` before being logged and propagated, ensuring the generation process is cleanly terminated via `BaseModel.STREAMING_FINISHED_EVENT`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_MODEL_NAME` — Specifies the name of the LLM model to use (defaults to 'gpt-4o').
- `AI_API_KEY` — The authentication key required to access the LLM provider's API.
- `AI_API_VERSION` — The specific API version string to use when communicating with the provider.
- `AI_AZURE_ENDPOINT` — The specific URL endpoint for connecting to Azure AI services.

**Module Dependencies:**
- **Standard/External:** `os`, `threading`, `gc`, `json`, `typing`, `httpx`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.tools.tool_registry.ToolRegistry](/ai/tools/tool_registry.md), [ai.core.llms.base_llm.BaseModel](/ai/core/llms/base_llm.md), [ai.core.llms.api_retry.LLMAPIError](/ai/core/llms/api_retry.md), [ai.core.llms.api_retry.RetryPolicy](/ai/core/llms/api_retry.md), [ai.core.llms.api_retry.call_with_retry](/ai/core/llms/api_retry.md), [ai.core.llms.api_retry.stream_with_retry](/ai/core/llms/api_retry.md), [ai.color.Color](/ai/color.md).