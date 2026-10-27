## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ChatService |
| Source file | chat.py |

The **ChatService** acts as the high-level orchestration layer for all conversational interactions within the server module. It serves as the primary interface between incoming HTTP chat requests and the underlying intelligence engine, managing the lifecycle of a chat completion from session routing to final response delivery.

**Functional Mission**
The primary responsibility of **ChatService** is to orchestrate the complex workflow required to fulfill a chat completion request. This includes resolving session-specific memory paths, selecting and configuring the appropriate LLM "brain," resolving system prompts via external loaders, and managing the delivery of both streaming and non-streaming responses. It effectively abstracts the complexities of session management and model configuration away from the API routing layer.

**System Context & Integration**
This component sits at the center of the chat execution flow. It receives `ChatCompletionRequest` objects and coordinates with [BrainHub](/docs/ai/modules/server/brain_hub.md) to ensure the correct model and history are loaded. It utilizes [PromptLoader](/docs/ai/services/prompt_loader.md) to resolve complex system instructions and relies on [ChatMessageFormatter] to standardize message structures. Once the LLM generates content, the service interacts with [BrainHub](/docs/ai/modules/server/brain_hub.md) to persist the conversation history, ensuring continuity in subsequent turns.

- **INTERNAL REFERENCES**: [BrainHub](/docs/ai/modules/server/brain_hub.md), [PromptLoader](/docs/ai/services/prompt_loader.md), [ChatCompletionRequest](/docs/ai/modules/server/schemas.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `ACTIVE_SESSION` (via `ChatSessionRouter.build_session_path`)  Fallback session ID if none is provided in the request.

**Hardcoded Constants:**
- `default` (via `ChatSessionRouter.build_session_path`)  Default session ID used when no ID is specified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatSessionRouter` | Class | Manages directory creation and file path resolution for chat sessions. |
| `ChatMessageFormatter` | Class | Transforms raw message objects into standardized dictionary formats for LLM consumption. |
| `ChatResponseHandler` | Class | Manages the execution of LLM calls, handling both `StreamingResponse` and standard JSON responses. |
| `ChatService` | Class | The main orchestrator that integrates routing, brain resolution, and response handling. |
| `chat_completion` | Async Func | The primary entry point for processing a full chat request lifecycle. |
| `_resolve_system_prompt` | Method | Resolves string literals or file paths into actual system prompt content. |
| `_resolve_brain` | Method | Configures the [BrainHub](/docs/ai/modules/server/brain_hub.md) with the requested model and prompt. |

## 4. Execution Logic & Flow
- **Initialization**: The `ChatService` is instantiated with a `BrainHub` instance, a `session_root_dir` path, and a configuration dictionary. It initializes its internal helper classes (`ChatSessionRouter`, `ChatMessageFormatter`, `ChatResponseHandler`).
- **Data Path**: 
    1. **Input**: `ChatCompletionRequest` received via `chat_completion`.
    2. **Routing**: `ChatSessionRouter` determines the `.json` file path for the session and instructs `BrainHub` to route memory to that file.
    3. **Brain Setup**: `_resolve_brain` is called to load the specific model and resolve the system prompt via `PromptLoader`.
    4. **Formatting**: `ChatMessageFormatter` converts the request messages into a list of `{"role": ..., "content": ...}` dictionaries.
    5. **History Update**: The user's latest message is added to the `BrainHub` history.
    6. **Inference**: 
        - If `stream=True`: `ChatResponseHandler.stream_response` yields chunks via a generator.
        - If `stream=False`: `ChatResponseHandler.non_stream_response` waits for the full string.
    7. **Persistence**: The assistant's response is added to history and saved to the session JSON file.
    8. **Output**: A `StreamingResponse` or a dictionary containing the assistant's message.
- **Conditional Branching**:
    - **Stream Toggle**: Checks `request.stream` to decide between `stream_response` (async generator) or `non_stream_response` (blocking).
    - **Prompt Resolution**: `_resolve_system_prompt` checks if the input is a valid file reference via `PromptLoader`; if not, it treats the input as a literal string.
    - **Error Handling**: Catches exceptions during streaming to yield an error JSON payload, or catches inference errors during non-streaming to raise a `500 HTTPException`.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib`, `os`, `json`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [BrainHub](/docs/ai/modules/server/brain_hub.md)
    - [ChatCompletionRequest](/docs/ai/modules/server/schemas.md)
    - [PromptLoader](/docs/ai/services/prompt_loader.md)
- **External Packages**: `fastapi`