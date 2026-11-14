## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| EventBinder | ai/services/event_binder.md |

This component is responsible for centralizing and managing the event subscription lifecycle within the application. Its primary function, encapsulated in `EventBinder.bind_core_events`, is to establish connections between core application events—such as a chat message being sent or output being requested—and the specific callback functions provided by the user or service layer.

Architecturally, `EventBinder` acts as a service layer intermediary. It bridges the communication gap between the high-level `Chat` and `BaseModel` instances and the downstream business logic listeners. It relies on the event dispatching mechanisms implemented within [ai.chat.chat](/ai/chat/chat.md) and [ai.core.llms.base_llm.BaseModel](/ai/core/llms/base_llm.md) to ensure that state changes trigger the correct handlers.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| EventBinder.bind_core_events | Static Method | Binds core application events to their respective listeners. Accepts instances of Chat, BaseModel, and three specific callback functions to configure event listeners. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The method iterates through predefined application events (`chat.EVENT_CHAT_SENT`, `chat.EVENT_OUTPUT_REQUESTED`, and `BaseModel.STREAMING_FINISHED_EVENT`). For each event, it calls the respective `add_event` method on the provided `Chat` or `BaseModel` objects, registering the supplied callback function as the listener. It includes a safety check to ensure the `llm` instance is not null before attempting to bind the LLM stream finished event.

- **Side Effects:** Mutates the internal state of the `Chat` and `BaseModel` objects by registering new listeners/callbacks.

- **Error Handling:** Implicitly relies on the underlying `Chat.add_event` and `BaseModel.add_event` methods to handle internal event registration errors; no explicit exception handling is present in this component.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `typing`
- **Internal:** [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.chat.chat](/ai/chat/chat.md)