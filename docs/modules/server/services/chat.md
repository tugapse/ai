## 1. Architectural Role
Acts as the high-level orchestration layer for chat interactions, managing session-based memory routing, system prompt resolution, and the execution of both streaming and non-streaming LLM responses.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatSessionRouter` | Class | Manages session directory creation and routes memory to specific JSON files. |
| `build_session_path` | Method | Generates the filesystem path for session directories and target JSON files. |
| `route_memory` | Method | Triggers `BrainHub` to link the current session file to the active memory context. |
| `ChatMessageFormatter` | Class | Transforms raw message objects into a standardized list of role/content dictionaries. |
| `ChatResponseHandler` | Class | Executes the LLM inference and manages the lifecycle of streaming/non-streaming responses. |
| `_ensure_llm_available` | Method | Validates that the `brain_hub.orchestrator.llm` is initialized before processing. |
| `stream_response` | Method | Generates a `StreamingResponse` via an asynchronous event generator for real-time output. |
| `non_stream_response` | Method | Executes a blocking LLM call and returns a complete dictionary response. |
| `ChatService` | Class | The primary entry point that coordinates routing, prompt resolution, and response handling. |
| `_resolve_system_prompt` | Method | Uses `PromptLoader` to convert prompt identifiers into actual text content. |
| `_resolve_brain` | Method | Configures the `BrainHub` with the requested model and resolved system prompt. |
| `chat_completion` | Method | The main asynchronous workflow for processing a `ChatCompletionRequest`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `ChatSessionRouter` is instantiated with a `session_root_dir` and a configuration dictionary.
    - `ChatService` is instantiated, aggregating instances of `ChatSessionRouter`, `ChatMessageFormatter`, and `ChatResponseHandler`.
- **Data Path**: 
    - `ChatCompletionRequest` $\rightarrow$ `ChatSessionRouter.build_session_path` (Path Resolution) $\rightarrow$ `ChatSessionRouter.route_memory` (Memory Linking) $\rightarrow$ `ChatService._resolve_brain` (Model/Prompt Setup) $\rightarrow$ `ChatMessageFormatter.format_messages` (Data Normalization) $\rightarrow$ `BrainHub.add_history_message` (State Update) $\rightarrow$ `ChatResponseHandler` (LLM Inference) $\rightarrow$ `StreamingResponse` or `Dict` (Final Output).
- **Conditional Branching**:
    - **Stream Flag**: If `request.stream` is `True`, the logic enters `stream_response` (async generator); otherwise, it enters `non_stream_response`.
    - **Prompt Resolution**: `_resolve_system_prompt` checks if a prompt is a file reference via `PromptLoader`; if resolution fails, it falls back to using the input as literal text.
    - **LLM Availability**: `_ensure_llm_available` raises a 503 `HTTPException` if the LLM is `None`.
    - **Response Type**: `non_stream_response` checks if `raw_output` is a `str` or an iterable to determine how to aggregate text.

## 4. Resource Dependencies
- **Standard Libraries**: `pathlib.Path`, `os`, `json`, `typing`
- **Internal Modules**: `..brain_hub.BrainHub`, `..schemas.ChatCompletionRequest`, `services.config_helper.ProgramSetting`, `services.prompt_loader.PromptLoader`, `functions`
- **External Packages**: `fastapi.HTTPException`, `fastapi.responses.StreamingResponse`

## 5. Configuration & Environment
- **Hardcoded Constants**: `"default"` (fallback session ID), `"assistant"`/`"user"` (history roles), `"text/event-stream"` (media type), `"data: [DONE]\n\n"` (stream terminator).
- **Environment Lookups**: `config.get("ACTIVE_SESSION")` (used for default session identification).