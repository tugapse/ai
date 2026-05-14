## 1. Architectural Role
`chat.py` serves as the high-level orchestration layer for chat completion requests, acting as the bridge between incoming API schemas and the underlying intelligence engine. It manages the lifecycle of a chat interaction by routing session-specific memory via [brain_hub.md](modules/server/brain_hub.md), resolving system prompts through [prompt_loader.md](services/prompt_loader.md), selecting the appropriate LLM via the orchestrator, and handling both real-time streaming and monolithic responses. It encapsulates session persistence logic, message formatting, and error handling to ensure consistent interaction patterns within the server module.

## 2. Environment & Configuration
**Environment Lookups:**
- `ACTIVE_SESSION` (via `ChatSessionRouter.build_session_path`)  Fallback session identifier if none provided in the request.

**Hardcoded Constants:**
- `503` (Default: `HTTPException` status)  Returned when the LLM is not initialized.
- `500` (Default: `HTTPException` status)  Returned during inference failures.
- `"data: [DONE]\n\n"` (Default: `str`)  SSE terminator for streaming responses.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatSessionRouter` | Class | Manages directory creation and maps `ChatCompletionRequest` to physical JSON session files. |
| `ChatMessageFormatter` | Class | Transforms raw message objects into standard `{"role": "...", "content": "..."}` dictionaries. |
| `ChatResponseHandler` | Class | Orchestrates the execution of LLM `chat` calls, managing both `StreamingResponse` generation and synchronous text extraction. |
| `ChatService` | Class | The primary entry point; coordinates routing, prompt resolution, brain selection, and history updates. |
| `chat_completion` | Async Method | The main execution workflow for processing a `ChatCompletionRequest`. |

## 4. Execution Logic & Flow
- **Initialization**: `ChatService` instantiates its sub-components (`ChatSessionRouter`, `ChatMessageFormatter`, `ChatResponseHandler`) using the provided `BrainHub`, session directory, and configuration.
- **Data Path**:
    1. **Input**: `ChatCompletionRequest` object received.
    2. **Routing**: `ChatSessionRouter` resolves the directory and file path $\rightarrow$ `BrainHub` routes memory to the file.
    3. **Brain Resolution**: `ChatService` resolves the system prompt (via `PromptLoader`) and selects the LLM model.
    4. **Context Preparation**: Messages are formatted $\rightarrow$ User message is appended to `BrainHub` history.
    5. **Inference**:
        - **Stream Path**: `event_generator` iterates through LLM chunks $\rightarrow$ yields SSE formatted JSON $\rightarrow$ appends full response to history $\rightarrow$ signals `[DONE]`.
        - **Non-Stream Path**: LLM returns full content $\rightarrow$ response is parsed/joined $\rightarrow$ response is appended to history.
    6. **Output**: `StreamingResponse` or JSON dictionary.
- **Conditional Branching**:
    - `getattr(request, "stream", False)`: Determines whether to trigger the asynchronous generator or the synchronous completion path.
    - `isinstance(raw_output, str)`: Checks if the LLM returned a direct string or an iterable of chunks in non-streaming mode.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib`, `os`, `json`, `typing`
- **Internal Modules**: 
    - [brain_hub.md](modules/server/brain_hub.md)
    - [schemas.md](modules/server/schemas.md)
    - [config_helper.md](services/config_helper.md)
    - [prompt_loader.md](services/prompt_loader.md)
    - [functions.md](functions.md)
- **External Packages**: `fastapi`