## 1. Architectural Role
This file serves as the primary interactive terminal interface and input orchestration engine for the user. It implements a sophisticated REPL (Read-Eval-Print Loop) that manages user input via `prompt_toolkit`, handles multi-line text entry, facilitates file attachments through a staged "pending" mechanism, and manages command/agent mode transitions. It acts as a bridge between raw user keystrokes and the system's event-driven architecture by triggering lifecycle events in [core/events.md](core/events.md) and structuring messages according to [core/llms/base_llm.md](core/llms/base_llm.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `ChatRoles.USER` (Default: `"user"`)  Role identifier for user messages.
- `ChatRoles.ASSISTANT` (Default: `"assistant"`)  Role identifier for AI responses.
- `ChatRoles.SYSTEM` (Default: `"system"`)  Role identifier for system instructions.
- `ChatRoles.CONTROL` (Default: `"control"`)  Role identifier for control messages.
- `ChatRoles.TOOL` (Default: `"tool"`)  Role identifier for tool outputs.
- `max_chat_log` (Default: `50`)  Maximum number of messages to retain in memory.
- `terminate_tokens` (Default: `["quit", "q"]`)  Strings that trigger chat termination.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatRoles` | Class | Provides constant string identifiers for message roles. |
| `PrefixCompleter` | Class | Custom `prompt_toolkit` completion engine for `/` commands and `@` file paths. |
| `Chat` | Class | The core engine managing the input loop, state, and event dispatching. |
| `update_suggestions` | Method | Dynamically updates available command and agent lists. |
| `loop` | Method | Executes the continuous blocking input cycle. |
| `process_loop_frame` | Method | Handles the logic for a single input event (parsing commands, files, or chat). |
| `_handle_file_attachment`| Method | Reads file content from disk and stages it in `pending_files`. |
| `send_chat` | Method | Wraps content into a `BaseModel` message and triggers the chat event. |
| `run_command` | Method | Routes user input to specific command handlers like `/clear` or `/agent`. |
| `chat_finished` | Method | Finalizes the current turn and updates the message history. |

## 4. Execution Logic & Flow
- **Initialization**: Instantiates `PromptSession` with `InMemoryHistory`, sets up `KeyBindings` for multi-line toggling, and initializes empty state for `messages`, `pending_files`, and `agent_mode_active`.
- **Data Path**: 
    1. **Capture**: `prompt_session.prompt()` captures user input.
    2. **Classification**: 
        - If starts with `@`: Triggers `_handle_file_attachment` $\rightarrow$ Updates `pending_files`.
        - If starts with `/`: Triggers `run_command` $\rightarrow$ Executes internal command.
        - If `agent_mode_active`: Combines `pending_files` with input $\rightarrow$ Triggers `EVENT_AGENT_RUN_REQUESTED`.
        - Otherwise: Combines `pending_files` with input $\rightarrow$ Triggers `EVENT_CHAT_SENT`.
    3. **Transformation**: Text is wrapped into `BaseModel.create_message` objects.
    4. **Output**: Results are dispatched via events to be handled by external listeners.
- **Conditional Branching**:
    - `multiline_mode`: Determines if `prompt_toolkit` allows line breaks.
    - `agent_mode_active`: Changes input interpretation from standard chat to a single task execution.
    - `waiting_for_response` / `running_command`: Controls the UI state (toolbar and prompt prefix) and prevents overlapping input cycles.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `datetime`
- **Internal Modules**: 
    - [core/events.md](core/events.md)
    - [color.md](color.md)
    - [core/llms/base_llm.md](core/llms/base_llm.md)
    - [functions.md](functions.md)
- **External Packages**: `prompt_toolkit`