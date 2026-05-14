## 1. Architectural Role

**Functional Mission**
The **Chat** component serves as the primary interactive interface layer for the terminal-based user experience. Its core mission is to manage the lifecycle of a conversational session, handling complex user input patterns including command execution, file attachment staging, and multi-line text entry. It acts as a sophisticated input buffer that translates raw user keystrokes into structured messages or system commands.

**System Context & Integration**
This component functions as the bridge between the user and the underlying AI orchestration logic. It utilizes [Events](/docs/core/events.md) to broadcast state changes (such as `EVENT_CHAT_SENT` or `EVENT_AGENT_RUN_REQUESTED`) to downstream listeners. It integrates with [BaseModel](/docs/core/llms/base_llm.md) to structure message payloads and relies on [Color](/docs/color.md) for terminal UI feedback. By managing "pending files," it prepares context for the LLM, ensuring that file contents are injected into the prompt stream before being dispatched to the execution engine.

## 2. Environment & Configuration

**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `ChatRoles.USER` (Default: `"user"`)  Identifier for user-originated messages.
- `ChatRoles.ASSISTANT` (Default: `"assistant"`)  Identifier for AI-originated messages.
- `ChatRoles.SYSTEM` (Default: `"system"`)  Identifier for system-level instructions.
- `ChatRoles.CONTROL` (Default: `"control"`)  Identifier for internal control messages.
- `ChatRoles.TOOL` (Default: `"tool"`)  Identifier for tool-call outputs.
- `self.terminate_tokens` (Default: `["quit", "q"]`)  Strings that trigger session termination.
- `self.max_chat_log` (Default: `50`)  Limit for the in-memory message history buffer.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatRoles` | Class | Provides constant string identifiers for message roles. |
| `PrefixCompleter` | Class | Implements `prompt_toolkit.completion.Completer` for `/` command and `@` file path autocompletion. |
| `Chat` | Class | The main controller for the interactive loop, input handling, and event triggering. |
| `update_suggestions` | Method | Dynamically updates the available command and agent lists. |
| `_setup_key_bindings` | Method | Configures `prompt_toolkit` key bindings for toggling multi-line mode. |
| `_get_prompt_text` | Method | Generates the dynamic ANSI-formatted prompt string based on current mode and pending files. |
| `_get_bottom_toolbar` | Method | Generates the status bar text based on the current execution state. |
| `_add_message` | Method | Appends a message to the history and enforces the `max_chat_log` limit. |
| `_reset_chat` | Method | Clears messages, pending files, and top bar state. |
| `loop` | Method | The primary blocking execution loop for the chat interface. |
| `process_loop_frame` | Method | Orchestrates a single iteration of input capture, command parsing, and file attachment logic. |
| `_handle_file_attachment` | Method | Reads file contents from disk and stages them in `pending_files`. |
| `send_chat` | Method | Formats the final message (including staged files) and triggers the chat sent event. |
| `run_command` | Method | Dispatches internal commands (e.g., `/clear`, `/agent`) or external system commands. |
| `terminate_chat` | Method | Sets the termination flag to exit the loop. |
| `chat_finished` | Method | Finalizes the current turn by adding the assistant's response to the history. |

## 4. Execution Logic & Flow

- **Initialization**: 
    1. Initializes `Events` superclass.
    2. Sets up internal state: `messages` list, `pending_files` dictionary, and mode flags (`agent_mode_active`, `multiline_mode`).
    3. Configures `PromptSession` with `InMemoryHistory`.
    4. Instantiates `PrefixCompleter` with provided command/agent lists.
    5. Registers key bindings for `escape` + `enter` to toggle multi-line mode.

- **Data Path**:
    1. **Input Capture**: `prompt_session.prompt()` captures user input via the terminal.
    2. **Parsing**: 
        - If input starts with `@`: Path is parsed $\rightarrow$ File read $\rightarrow$ Content stored in `pending_files`.
        - If input starts with `/`: Input passed to `run_command`.
        - If `agent_mode_active` is True: Input + `pending_files` content $\rightarrow$ `EVENT_AGENT_RUN_REQUESTED`.
        - Standard Input: Input + `pending_files` content $\rightarrow$ `EVENT_CHAT_SENT`.
    3. **Output**: `func.out` renders formatted text to the console; `trigger` notifies external modules of the processed data.

- **Conditional Branching**:
    - **Multi-line Mode**: If `multiline_mode` is active, the prompt allows newlines; otherwise, `Enter` triggers immediate processing.
    - **Agent Mode**: If `/agent` is invoked, the system enters a state where the next input is treated as a task rather than a standard chat message.
    - **File Staging**: If `pending_files` is non-empty, the content is concatenated to the next message before transmission.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `datetime`
- **Internal Modules**: 
    - [Events](/docs/core/events.md)
    - [Color](/docs/color.md)
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [functions](/docs/functions.md)
- **External Packages**: `prompt_toolkit`