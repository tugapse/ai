## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **EventBinder** | [src/ai/services/event_binder.py](/src/ai/services/event_binder.py) |

The `EventBinder` class provides a centralized mechanism for connecting application-level event listeners to specific lifecycle events within the chat and LLM subsystems. It acts as a bridge that decouples the core logic of message handling and model streaming from the specific callback functions that react to those events.

This component serves as a utility service within the broader orchestration layer. By using `EventBinder`, the system can ensure that when a user sends a message via the [Chat](/AgentDocs/ai/chat/chat.md) instance or when a [BaseModel](/AgentDocs/ai/core/llms/base_llm.md) completes a stream, the appropriate high-level application logic is triggered without hardcoding those dependencies into the core classes.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `bind_core_events(chat, llm, start_chat_callback, output_requested_callback, llm_stream_finished_callback)` | Static Method | Orchestrates the registration of four specific event listeners: `EVENT_CHAT_SENT` and `EVENT_OUTPUT_REQUESTED` on the `Chat` instance, and `STREAMING_FINISHED_EVENT` on the `BaseModel` instance. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class uses a static method to perform batch registration of callbacks. It accesses event constants defined within the `Chat` class and the `BaseModel` class. It includes a safety check to ensure the `llm` instance is not `None` before attempting to bind the streaming finished event.
- **Side Effects:** This component mutates the internal state of the provided `Chat` and `BaseModel` instances by adding listeners to their respective event registries.
- **Error Handling:** The method performs a null-check on the `llm` parameter to prevent `AttributeError` when attempting to access `llm.add_event`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `typing.Callable`
- **Internal:**
    - [ai.core.llms.base_llm.BaseModel](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.chat.chat.Chat](/AgentDocs/ai/chat/chat.md)