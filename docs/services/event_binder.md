## 1. Architectural Role
The `EventBinder` acts as a static orchestration utility responsible for the decoupling of core application logic from specific event implementations. It serves as the central wiring mechanism that connects lifecycle events from the [chat](chat/chat.md) system and the [base_llm](core/llms/base_llm.md) engine to external callback functions, ensuring that message transmission, output requests, and stream completions are properly routed within the application lifecycle.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EventBinder` | Class | Provides static methods for attaching event listeners to core modules. |
| `bind_core_events` | Static Method | Orchestrates the attachment of specific callbacks to `Chat` and `BaseModel` event registries. |

## 4. Execution Logic & Flow
- **Initialization**: The class is stateless and accessed via static method calls; no instance state is maintained.
- **Data Path**: 
    1. Receives instances of [chat](chat/chat.md) and [base_llm](core/llms/base_llm.md) along with four `Callable` arguments.
    2. Accesses the event registry of the provided `chat` object.
    3. Accesses the event registry of the provided `llm` object.
    4. Registers the provided callbacks to the internal event dispatchers of the target objects.
- **Conditional Branching**: 
    - Performs a null-check on the `llm` parameter; if the LLM instance is provided, it proceeds to bind the `STRTEAING_FINISHED_EVENT`; if `None`, it skips LLM event binding to prevent attribute errors.

## 5. Resource Dependencies
- **Standard Libraries**: 
    - `typing` (for `Callable`)
- **Internal Modules**: 
    - [core/llms/base_llm.md](core/llms/base_llm.md)
    - [chat/chat.md](chat/chat.md)
- **External Packages**: None identified.