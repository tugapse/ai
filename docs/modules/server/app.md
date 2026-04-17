## 1. Architectural Role
Provides a FastAPI-based REST interface that exposes LLM inference capabilities, supporting both synchronous JSON responses and asynchronous Server-Sent Event (SSE) streaming via an injected orchestrator.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatMessage` | Class | Pydantic schema for individual message objects (role, content). |
| `ChatCompletionRequest` | Class | Pydantic schema for inference requests (messages, model, system_prompt, stream, temperature). |
| `create_app` | Func | Factory function that initializes the FastAPI instance and defines route handlers. |
| `health` | Func | GET endpoint returning system status and active model name. |
| `shutdown` | Func | POST endpoint acknowledging a shutdown request. |
| `chat_completions` | Func | POST endpoint handling model swapping and LLM inference (Standard/Streaming). |

## 3. Execution Logic & Flow
- **Initialization**: `create_app` is called with an `orchestrator` instance, which is captured in the closure of the route handlers.
- **Data Path**: `ChatCompletionRequest` $\rightarrow$ Model Validation/Swap $\rightarrow$ `orchestrator.llm.chat()` $\rightarrow$ `StreamingResponse` (SSE) OR JSON Response.
- **Conditional Branching**:
    1. **Orchestrator Check**: If `orchestrator` is None $\rightarrow$ Raise 503 HTTPException.
    2. **Neural Swap**: If `orchestrator.llm` is missing OR `active_model_id` $\neq$ `requested_model` $\rightarrow$ Execute `orchestrator.load()`.
    3. **Response Mode**:
        - If `request.stream` is `True` $\rightarrow$ Execute `event_generator()` yielding SSE formatted chunks.
        - If `request.stream` is `False` $\rightarrow$ Execute synchronous chat and return aggregated JSON.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `typing`
- **Internal Modules**: `color`
- **External Packages**: `fastapi`, `pydantic` (imported as `pydantic` in source)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `title`: "JARVIS Neural Hub"
    - `default_model`: "default"
    - `default_temperature`: 0.7
    - `media_type`: "text/event-stream"