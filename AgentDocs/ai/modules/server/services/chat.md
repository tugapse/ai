## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Chat Service Orchestrator** | [src/ai/modules/server/services/chat.py](/src/ai/modules/server/services/chat.py) |

The `chat.py` module provides the high-level orchestration logic for handling chat completion requests within the server module. It serves as the primary bridge between incoming API requests and the underlying AI capabilities, managing the lifecycle of a single chat interaction from session routing to final response delivery.

The component is responsible for resolving session paths, routing memory context via the [BrainHub](/ai/modules/server/brain_hub.md), resolving system prompts using the [PromptLoader](/ai/services/prompt_loader.md), and managing both streaming (SSE) and synchronous LLM responses. It ensures that user messages are correctly formatted and persisted into the session history.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatSessionRouter` | Class | Manages the identification and directory routing of chat sessions based on request parameters. |
| `ChatMessageFormatter` | Class | A utility class that transforms raw message objects into standardized dictionary formats for LLM consumption. |
| `ChatResponseHandler` | Class | Manages the execution of LLM calls, handling both `StreamingResponse` generation and standard synchronous dictionary responses. |
| `ChatService` | Class | The primary orchestrator that integrates routing, prompt resolution, brain configuration, and response handling. |
| `ChatService.chat_completion()` | Method | The main entry point for processing a [ChatCompletionRequest](/ai/modules/server/schemas.md). Returns a `StreamingResponse` or a dictionary. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Session Routing:** Uses `ChatSessionRouter` to construct filesystem paths for session JSON files, ensuring directories exist via `os.makedirs`.
    - **Brain Resolution:** The `ChatService` resolves the requested model and system prompt (via `PromptLoader`), then instructs the [BrainHub](/ai/modules/server/brain_hub.md) to load the appropriate configuration.
    - **Response Generation:** `ChatResponseHandler` checks LLM availability via the `BrainHub` orchestrator. For streaming, it uses an asynchronous generator to yield Server-Sent Events (SSE) formatted as JSON payloads.
- **Side Effects:**
    - **Filesystem:** Creates directories and writes/updates session JSON files to store chat history.
    - **Logging/Debugging:** Utilizes `ai.functions` for logging and debugging output.
    - **Network:** Generates `StreamingResponse` objects intended for HTTP/SSE transport.
- **Error Handling:**
    - Throws `fastapi.HTTPException` with status `503` if the LLM is not initialized.
    - Throws `fastapi.HTTPException` with status `500` if inference or non-streaming execution fails.
    - Catches exceptions during streaming to yield error payloads within the SSE stream.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ACTIVE_SESSION`  (Via `config` dict) Fallback session ID if no ID is provided in the request.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `os`, `json`, `typing`, `fastapi`.
- **Internal:**
    - [ai.functions](/ai/functions.md)
    - [ai.modules.server.brain_hub](/ai/modules/server/brain_hub.md)
    - [ai.modules.server.schemas](/ai/modules/server/schemas.md)
    - [ai.services.prompt_loader](/ai/services/prompt_loader.md)