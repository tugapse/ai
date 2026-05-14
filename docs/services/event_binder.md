## 1. Architectural Role

**Functional Mission**
The **EventBinder** class serves as a centralized orchestration utility designed to decouple event registration from the core logic of chat and language model instances. Its primary mission is to facilitate the wiring of specific application-level callbacks to the internal event systems of [Chat](/docs/chat/chat.md) and [BaseModel](/docs/core/llms/base_llm.md), ensuring that lifecycle events (such as message transmission or stream completion) trigger the appropriate downstream handlers.

**System Context & Integration**
This component acts as a bridge during the initialization phase of the application's execution flow. By consuming instances of [Chat](/docs/chat/chat.md) and [BaseModel](/docs/core/llms/base_llm.md), it establishes the reactive links necessary for the system to respond to user inputs and LLM outputs. It sits between the low-level event emitters and the high-level service logic, ensuring that when a state change occurs in the communication or inference layers, the rest of the system is notified via the provided callback functions.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EventBinder` | Class | Static utility class for managing event listener bindings. |
| `bind_core_events` | Func | Orchestrates the attachment of four specific callbacks to the `chat` and `llm` instances. |

## 4. Execution Logic & Flow
- **Initialization**: The method is invoked statically, requiring pre-instantiated objects for `chat` and `llm`, along with four functional callbacks.
- **Data Path**: 
    1. Receives `chat` and `llm` objects.
    2. Accesses `chat.EVENT_CHAT_SENT` and `chat.EVENT_OUTPUT_REQUESTED` to register `start_chat_callback` and `output_requested_callback` respectively.
    3. Checks for the existence of the `llm` object.
    4. Accesses `BaseModel.STRTEAING_FINISHED_EVENT` to register `llm_stream_finished_callback`.
- **Conditional Branching**: 
    - `if llm:`: A safety check is performed to prevent attribute errors if the LLM instance is `None`, ensuring the `llm_stream_finished_callback` is only bound if a valid model is provided.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [Chat](/docs/chat/chat.md)
- **External Packages**: None identified.