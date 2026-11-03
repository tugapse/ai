## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Chat Service Orchestrator** | [src/ai/modules/server/services/chat.py](/AgentDocs/ai/modules/server/services/chat.md) |

The `chat.py` module provides the high-level orchestration logic required to handle chat completion requests within the server module. It acts as the primary coordinator between incoming API requests, session management, memory routing, and the Large Language Model (LLM) execution engine.

Its primary responsibility is to manage the lifecycle of a single chat interaction: resolving the correct session directory, routing memory context via the `BrainHub`, resolving system prompts using the `PromptLoader`, and dispatching the request to either a streaming or synchronous response handler. It serves as the bridge between the raw HTTP layer (FastAPI) and the core AI logic.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatSessionRouter` | Class | Manages directory resolution and memory routing for specific chat sessions. |
| `ChatSessionRouter.build_session_path()` | Method | Calculates the filesystem path for a session based on `ChatCompletionRequest`. |
| `ChatSessionRouter.route_memory()` | Method | Instructs `BrainHub` to point its memory context to a specific JSON session file. |
| `ChatMessageFormatter` | Class | Utility for converting raw message objects into standard LLM dictionary formats. |
| `ChatMessageFormatter.format_messages()` | Static Method | Transforms a list of messages and extracts the most recent user content. |
| `ChatResponseHandler` | Class | Manages the execution of LLM calls, supporting both SSE streaming and standard JSON responses. |
| `ChatResponseHandler.stream_response()` | Async Method | Returns a `StreamingResponse` yielding Server-Sent Events (SSE) for real-time text generation. |
| `ChatResponseHandler.non_stream_response()` | Method | Executes a synchronous LLM call and returns a complete dictionary response. |
| `ChatService` | Class | The top-level service class that orchestrates the full chat workflow. |
| `ChatService.chat_completion()` | Async Method | The main entry point that coordinates routing, brain resolution, and response handling. |

## 3. Implementation Details & Side Effects

### Core Logic
- **Session Management:** Uses `ChatSessionRouter` to ensure session files are stored in the correct subdirectories. It defaults to an `ACTIVE_SESSION` from the config if no ID is provided.
- **Brain Resolution:** The `ChatService._resolve_brain` method prepares the `BrainHub` by loading specific model configurations and resolving system prompts (which can be literal strings or references to files via `PromptLoader`).
- **Response Generation:** 
    - **Streaming:** Uses an internal `event_generator` to wrap LLM chunks into SSE `data: {...}` payloads. It manually accumulates the full response to save it to history upon completion.
    - **Non-Streaming:** Collects all chunks from the LLM and returns a single JSON-compatible dictionary.
- **History Persistence:** After every successful interaction (streaming or non-streaming), the assistant's response is added to the `BrainHub` history and persisted to the filesystem via `save_history_to_json`.

### Side Effects
- **Filesystem:** Creates directories via `os.makedirs` and writes/updates `.json` session files.
- **Logging:** Extensive use of `func.log` and `func.debug` for operational visibility.
- **Network:** Returns `StreamingResponse` (SSE) for streaming requests.

### Error Handling
- **LLM Availability:** Throws `fastapi.HTTPException` (503 Service Unavailable) if the `BrainHub` orchestrator has no initialized LLM.
- **Inference Failures:** Catches exceptions during non-streaming inference and re-raises them as `fastapi.HTTPException` (500 Internal Server Error).
- **Streaming Errors:** Catches exceptions within the generator and yields an error payload via the SSE stream.

## 4. Dependencies & Configuration

**Environment & Configuration:**
- `config["ACTIVE_SESSION"]`  Used by `ChatSessionRouter` as a fallback session ID if none is provided in the request.

**Module Dependencies:**
- **Standard/External:** `pathlib`, `os`, `json`, `typing`, `fastapi`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.modules.server.brain_hub](/AgentDocs/ai/modules/server/brain_hub.md)
    - [ai.modules.server.schemas](/AgentDocs/ai/modules/server/schemas.md)
    - [ai.services.prompt_loader](/AgentDocs/ai/services/prompt_loader.md)