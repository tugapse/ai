## 1. Architectural Role
Manages the binding of event listeners for chat and LLM events.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EventBinder` | Class | Binds core application events to their respective listeners. |
| `bind_core_events` | Static Method | Binds chat and LLM events to callback functions. |

## 3. Execution Logic & Flow
- **Initialization**: No explicit initialization occurs.
- **Data Path**: 
  1. The method `bind_core_events` is called with parameters: `chat`, `llm`, `start_chat_callback`, `output_requested_callback`, and `llm_stream_finished_callback`.
  2. The `chat` instance adds an event listener for `EVENT_CHAT_SENT` using the `start_chat_callback`.
  3. The `chat` instance adds an event listener for `EVENT_OUTPUT_REQUESTED` using the `output_requested_callback`.
  4. If the `llm` instance exists, it adds an event listener for `STREAMING_FINISHED_EVENT` using the `llm_stream_finished_callback`.
- **Conditional Branching**: 
  - Checks if the `llm` instance exists before attempting to add an event listener.

## 4. Resource Dependencies
- **Standard Libraries**: None
- **Internal Modules**: `core.llms.base_llm`, `core.chat`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None