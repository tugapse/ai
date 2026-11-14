## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| GeminiAPIModel | /ai/core/llms/gemini.md |

This component implements the `GeminiAPIModel` class, serving as the primary interface for interacting with Google's Gemini models via both the standard Gemini API and Google Vertex AI. Its core responsibility is to encapsulate the complex logic of initializing the client, managing API credentials (key or ADC), converting proprietary internal message formats into the specific `google-genai` API structures, and handling the streaming or synchronous execution of generation requests.

This class functions as a specialized service layer within the application's AI core. It abstracts away the low-level details of LLM communication, allowing higher-level components to interact with the model using a unified `BaseModel` interface. It relies on utilities from [ai.core.llms.base_llm](/ai/core/llms/base_llm.md) for base functionality, [ai.core.llms.api_retry](/ai/core/llms/api_retry.md) for resilience, and [ai.tools.tool_registry](/ai/tools/tool_registry.md) for function calling parsing.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `GeminiAPIModel` | Class | Implements the Gemini API model interface, supporting both direct API key usage and Google Vertex AI integration. |
| `chat` | Method | Executes the chat/generation request. Takes a list of messages, optional images, and stream/options flags. Returns a generator if streaming is enabled, or the response text/action if synchronous. |
| `load_images` | Method | Loads a list of image inputs (either file paths or PIL objects) and converts them into the `types.Part` format required by the API. |
| `is_gpu_available` | Method | Checks if GPU resources are available for the current execution context. |
| `clean_cache` | Method | Forces a garbage collection cycle to free up memory. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `chat` method first constructs a dynamic system prompt, ensuring the internal system instruction is prioritized. It then converts the internal message list using `_convert_messages_to_api`, which handles role mapping and special content serialization (like tool calls). The generation is executed either synchronously via `_generate_response_sync` or streamed via `_stream_generator`. The streaming path meticulously intercepts chunks to check for sentinel tags, allowing for early termination or extraction of structured tool call data.
- **Side Effects:** The code interacts heavily with external systems: it makes network calls to the Gemini/Vertex AI endpoints, reads environment variables (`GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`), and may spawn external processes (`gcloud`) during authentication checks.
- **Error Handling:** It uses `LLMAPIError` and `Exception` wrapping within the retry mechanism (`stream_with_retry`/`call_with_retry`) to catch and re-raise API-specific or general errors, ensuring that the caller receives a typed error rather than raw connection issues.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `GEMINI_API_KEY` — The direct API key for Gemini Developer mode. If unset, the class attempts to use this key.
- `GOOGLE_CLOUD_PROJECT` — The GCP project ID used when operating in Vertex AI mode.

**Module Dependencies:**
- **Standard/External:** `os`, `io`, `gc`, `subprocess`, `warnings`, `json`, `google-genai`, `PIL` (used internally via `load_images`).
- **Internal:** [ai.functions](/ai/functions.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.core.llms.api_retry](/ai/core/llms/api_retry.md), [ai.color](/ai/color.md), [ai.tools.tool_registry](/ai/tools/tool_registry.md).