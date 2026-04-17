## 1. Architectural Role
The `Chat` component manages the interactive CLI session, handling user input via `prompt_toolkit`, managing file staging, and orchestrating the dispatch of chat messages and system commands through an event-driven architecture.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatRoles` | Class | Constant definitions for message roles (`USER`, `ASSISTANT`, `SYSTEM`, `CONTROL`, `TOOL`). |
| `PrefixCompleter` | Class | Implements Tab-completion for commands (starting with `/`) and filesystem paths (starting with `@`). |
| `Chat` | Class | Main controller for the chat loop, input processing, and event triggering. |
| `Chat.loop` | Method | Entry point that continuously executes `process_loop_frame` until `terminate` is True. |
| `Chat.process_loop_frame` | Method | Handles the prompt lifecycle: captures input, processes file attachments, and routes to commands or chat. |
| `Chat.send_chat` | Method | Packages user input and staged files into a message and triggers `EVENT_CHAT_SENT`. |
| `Chat.run_command` | Method | Parses and executes internal commands (`/clear`, `/agent`) or triggers `EVENT_COMMAND_STARTED`. |
| `Chat.chat_finished` | Method | Finalizes the assistant's response cycle and updates the message history. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Inherits from `Events`.
    2. Initializes state flags (`terminate`, `running_command`, `waiting_for_response`).
    3. Sets up message buffers (`messages`, `pending_files`) and UI configurations.
    4. Instantiates `PromptSession` and configures `KeyBindings` for multiline mode toggle.
- **Data Path**: 
    1. **Input**: `prompt_session.prompt` captures raw string $\rightarrow$ `user_input_stripped`.
    2. **Processing**: 
        - If `@path`: File content is read and stored in `pending_files`.
        - If `/command`: Routed to `run_command` $\rightarrow$ `EVENT_COMMAND_STARTED` or `EVENT_AGENT_RUN_REQUESTED`.
        - If text: Combined with `pending_files` content $\rightarrow$ `send_chat`.
    3. **Output**: `trigger(EVENT_CHAT_SENT)` $\rightarrow$ `func.out` (UI display).
- **Conditional Branching**:
    - **Input Prefix**: `/` (Command) vs `@` (File Attachment) vs Text (Chat).
    - **Command Type**: `/clear` (Reset state) vs `/agent` (Agent request) vs Other (General command).
    - **UI State**: `multiline_mode` determines if `Enter` sends the message or adds a newline.
    - **System State**: `waiting_for_response` or `running_command` modifies the `bottom_toolbar` display.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `datetime`
- **Internal Modules**: `core.events.Events`, `color.Color`, `color.format_text`, `functions` (as `func`), `core.llms.base_llm.BaseModel`
- **External Packages**: `prompt_toolkit` (`PromptSession`, `InMemoryHistory`, `ANSI`, `KeyBindings`, `Condition`, `Completer`, `Completion`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `terminate_tokens`: `["quit", "q"]`
    - `max_chat_log`: `50`
    - `user_prompt`: `"User: "`
- **Environment Lookups**: None.