## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **EventBinder** | [src/ai/services/event_binder.py](/AgentDocs/ai/services/event_binder.md) |

The `EventBinder` component is a utility service responsible for orchestrating the connection between core application events and their corresponding callback listeners. It centralizes the logic required to wire up the event systems of the chat interface and the Large Language Model (LLM) engine, ensuring that lifecycle eventssuch as message transmission or stream completiontrigger the appropriate application responses.

Within the broader architecture, this component acts as a configuration bridge during the initialization phase of the application. By decoupling the event registration logic from the primary business logic of the `Chat` and `BaseModel` classes, it provides a clean, single point of entry for managing the reactive behavior of the system.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `EventBinder` | Class | A static utility class used to manage event listener bindings. |
| `bind_core_events(...)` | Static Method | Attaches specific callback functions to `Chat` and `BaseModel` events. Requires a `Chat` instance, a `BaseModel` instance, and four callable listeners. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses the `add_event` method available on both `Chat` and `BaseModel` instances. It maps predefined event constants (e.g., `EVENT_CHAT_SENT`, `EVENT_OUTPUT_REQUESTED`, and `STREAMING_FINISHED_EVENT`) to the provided user-defined callback functions.
- **Side Effects:** This component mutates the internal state of the passed `Chat` and `BaseModel` instances by registering new listeners in their respective event registries.
- **Error Handling:** The implementation includes a safety check to ensure the `llm` instance is not `None` before attempting to bind `STREAMING_FINISHED_EVENT`. If `llm` is null, the LLM-specific event binding is skipped.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing.Callable`
- **Internal:** 
    - [ai.core.llms.base_llm.BaseModel](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.chat.chat.Chat](/AgentDocs/ai/chat/chat.md)