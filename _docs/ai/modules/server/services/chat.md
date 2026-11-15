## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ChatService | /ai/modules/server/services/chat.md |

This component provides the high-level orchestration layer for all chat interactions within the system. Its primary responsibility is managing the entire lifecycle of a user query, from determining the correct conversational context to executing the LLM inference and formatting the final response for the client. It bridges the gap between incoming API requests and the core AI processing capabilities.

Architecturally, this service acts as a critical controller within the application backend. It utilizes [ChatSessionRouter](/ai/modules/server/services/chat.md) to manage session persistence, relies on [ChatMessageFormatter](/ai/modules/server/services/chat.md) for data preparation, and delegates the actual LLM interaction and history saving to [ChatResponseHandler](/ai/modules/server/services/chat.md). It coordinates with the [BrainHub](/ai/modules/server/brain_hub.md) to acquire necessary resources like models and memory context.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatSessionRouter` | Class | Manages the routing and identification of chat sessions by building file paths based on request parameters. |
| `ChatSessionRouter.build_session_path` | Method | Determines the full path and ID for the target session based on the `ChatCompletionRequest`. |
| `ChatSessionRouter.route_memory` | Method | Routes the memory context to the specified session file within the [BrainHub](/ai/modules/server/brain_hub.md). |
| `ChatMessageFormatter` | Class | Utility for converting raw message objects into a standardized list format suitable for LLM API calls. |
| `ChatMessageFormatter.format_messages` | Method | Converts a list of message objects into a list of dictionaries and extracts the last user message content. |
| `ChatResponseHandler` | Class | Handles the execution and formatting of the LLM response, supporting both streaming and non-streaming modes. |
| `ChatResponseHandler._ensure_llm_available` | Method | Checks if the LLM component within the [BrainHub](/ai/modules/server/brain_hub.md) orchestrator is initialized, raising an error if it is not. |
| `ChatResponseHandler.stream_response` | Method | Generates a streaming HTTP response by calling the LLM in streaming mode, yielding SSE data. |
| `ChatResponseHandler.non_stream_response` | Method | Generates a standard, non-streaming HTTP response by calling the LLM synchronously. |
| `ChatService` | Class | High-level chat orchestration service managing the entire chat interaction lifecycle. |
| `ChatService._resolve_system_prompt` | Method | Resolves the system prompt content, attempting to load it from a template or file via [PromptLoader](/ai/services/prompt_loader.md). |
| `ChatService._ensure_no_agent_run` | Method | Checks if an agent run is already in progress, raising a conflict error if true. |
| `ChatService._resolve_brain` | Method | Acquires a `ModelLease` from the [BrainHub](/ai/modules/server/brain_hub.md) after resolving model and system prompt configurations. |
| `ChatService._decode_images` | Method | Converts base64 encoded image URLs into PIL Image objects, validating model support. |
| `ChatService.generation_options` | Method | Transforms request-level sampling settings into engine-specific options, handling differences like `max_tokens` vs `max_new_tokens`. |
| `ChatService.chat_completion` | Method | Main entry point: orchestrates memory routing, brain resolution, formatting, and invokes the appropriate response handler. |
| `ChatService._complete` | Method | Executes the actual chat turn on the acquired model lease, handling streaming or synchronous completion. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `chat_completion` method drives the flow: it first routes the session memory via [ChatSessionRouter](/ai/modules/server/services/chat.md). It then uses `asyncio.to_thread` to synchronously acquire a `ModelLease` via `_resolve_brain`, which waits for the correct model to become available on the [BrainHub](/ai/modules/server/brain_hub.md). Finally, it calls `_complete`, which formats the messages and executes the LLM call either as a stream or a single synchronous request, ensuring history is saved afterward.
- **Side Effects:** Reads/writes to the filesystem (via session file management in [ChatSessionRouter](/ai/modules/server/services/chat.md) and history saving in [ChatResponseHandler](/ai/modules/server/services/chat.md)). Interacts with external resources (LLM via [BrainHub](/ai/modules/server/brain_hub.md)).
- **Error Handling:** Raises `HTTPException` for various failures: 409 (Agent in progress), 404 (Model not found), 503 (LLM not initialized), 400 (Image decoding failure), and 500 (Inference/System errors). `ModelBusyError` is caught during brain acquisition to return a 409.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `asyncio`, `os`, `json`, `typing`, `fastapi`, `PIL` (via `from PIL import Image`).
- **Internal:** [PromptLoader](/ai/services/prompt_loader.md), [BrainHub](/ai/modules/server/brain_hub.md), [ChatSessionRouter](/ai/modules/server/services/chat.md), [ChatMessageFormatter](/ai/modules/server/services/chat.md), [ChatResponseHandler](/ai/modules/server/services/chat.md).