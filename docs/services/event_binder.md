## 1. Architectural Role
Provides a centralized mechanism to link specific event triggers from `Chat` and `BaseModel` instances to their corresponding callback handler functions.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EventBinder` | Class | Container for event binding logic. |
| `bind_core_events` | Static Method | Registers three specific callbacks to `chat` and `llm` event systems. |

## 3. Execution Logic & Flow
- **Initialization**: No instance state; the class operates via a static method.
- **Data Path**: 
    1. Receives `Chat` instance, `BaseModel` instance, and three `Callable` callbacks.
    2. Maps `chat.EVENT_CHAT_SENT` $\rightarrow$ `start_chat_callback`.
    3. Maps `chat.EVENT_OUTPUT_REQUESTED` $\rightarrow$ `output_requested_callback`.
    4. Maps `BaseModel.STREAMING_FINISHED_EVENT` $\rightarrow$ `llm_stream_finished_callback` (conditional).
- **Conditional Branching**: 
    - `if llm:`: Checks for the existence of the `BaseModel` instance before attempting to register the streaming finished event to prevent null reference errors.

## 4. Resource Dependencies
- **Standard Libraries**: `typing.Callable`
- **Internal Modules**: `core.llms.base_llm.BaseModel`, `core.chat.Chat`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `chat.EVENT_CHAT_SENT`
    - `chat.EVENT_OUTPUT_REQUESTED`
    - `BaseModel.STREAMING_FINISHED_EVENT`
- **Environment Lookups**: None