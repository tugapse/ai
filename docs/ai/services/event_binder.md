## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | EventBinder |
| Source file | event_binder.py |

The **EventBinder** serves as a centralized orchestration utility designed to decouple the registration of event listeners from the core logic of the chat and LLM modules. By providing a static interface for event binding, it ensures that the application's reactive components are wired together in a consistent and predictable manner during the system initialization phase.

**Functional Mission**
The primary responsibility of **EventBinder** is to automate the connection between specific system events (such as chat messages being sent or LLM streams concluding) and their corresponding callback functions. It solves the problem of manual, scattered event registration by providing a single, unified method to bind high-level application workflows to the underlying event emitters.

**System Context & Integration**
This component acts as a bridge during the setup phase of the application execution flow. It takes active instances of [Chat](/docs/ai/chat/chat.md) and [BaseModel](/docs/ai/core/llms/base_llm.md) and injects functional callbacks into them. This integration allows downstream modules to react to real-time state changessuch as UI updates or loggingwithout the [Chat](/docs/ai/chat/chat.md) or [BaseModel](/docs/ai/core/llms/base_llm.md) modules needing direct knowledge of the specific callback implementations.

- **INTERNAL REFERENCES**: [Chat](/docs/ai/chat/chat.md), [BaseModel](/docs/ai/core/llms/base_llm.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EventBinder` | Class | A utility class containing static methods for event orchestration. |
| `bind_core_events` | Func | Orchestrates the attachment of four specific callbacks to the `Chat` and `BaseModel` event systems. |

## 4. Execution Logic & Flow
- **Initialization**: The class is used statelessly via its static method `bind_core_events`. It requires pre-instantiated `Chat` and `BaseModel` objects, along with four `Callable` arguments representing the desired reaction logic.
- **Data Path**: 
    1. Receives `Chat` and `BaseModel` instances.
    2. Accesses `chat.EVENT_CHAT_SENT` and `chat.EVENT_OUTPUT_REQUESTED` constants.
    3. Accesses `BaseModel.STREAMING_FINISHED_EVENT` constant.
    4. Executes `add_event` on the target objects to register the provided callbacks.
- **Conditional Branching**: 
    - **LLM Existence Check**: The method performs a null check on the `llm` parameter (`if llm:`). If the LLM instance is provided, it proceeds to bind the `STREAMING_FINISHED_EVENT`; if `None`, it skips LLM event binding to prevent attribute errors.

## 5. Resource Dependencies
- **Standard Libraries**: `typing` (Callable)
- **Internal Modules**: 
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [Chat](/docs/ai/chat/chat.md)
- **External Packages**: None identified.