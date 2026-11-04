## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Chat Engine** | [src/ai/chat/chat.py](/src/ai/chat/chat.py) |

The `Chat` component is a terminal-based interactive session manager designed to facilitate human-AI communication. It handles the complexities of a command-line interface (CLI), including multi-line input modes, real-time command completion, and a sophisticated file attachment workflow that allows users to "stage" files for inclusion in subsequent prompts.

As a core UI and interaction controller, it sits between the user's terminal and the underlying AI logic. It manages the conversational state, processes specialized commands (prefixed with `/`), and orchestrates "Agent Mode," where user input is treated as a high-level task rather than a simple chat message. It leverages an event-driven architecture to signal state changes like `EVENT_CHAT_SENT` or `EVENT_AGENT_RUN_REQUESTED` to the rest of the system.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatRoles` | Class | A constant provider defining standard roles: `USER`, `ASSISTANT`, `SYSTEM`, `CONTROL`, and `TOOL`. |
| `PrefixCompleter` | Class | A `prompt_toolkit` custom completer providing tab-completion for commands (`/`) and file paths (`@`). |
| `Chat` | Class | The primary controller for the interactive session. |
| `Chat.loop()` | Method | Starts the blocking infinite loop that processes the user input frame by frame. |
| `Chat.update_suggestions()` | Method | Dynamically updates the available command and agent lists for the completer. |
| `Chat.send_chat(message_content)` | Method | Formats a user message, adds it to the history, and triggers the `EVENT_CHAT_SENT` event. |
| `Chat.run_command(message)` | Method | Executes internal commands like `/clear` or `/agent` (which toggles agent mode). |
| `Chat.terminate_chat()` | Method | Sets the termination flag to exit the input loop gracefully. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Input Loop:** Uses `prompt_toolkit` to manage a sophisticated REPL. It supports a `multiline_mode` toggled by `Escape + Enter`.
    - **Deferred File Attachment:** When a user inputs a path starting with `@`, the system reads the file and stores it in `pending_files`. This content is then automatically prepended to the *next* message sent via `send_chat` or used as context for an agent task.
    - **Command Dispatch:** Inputs starting with `/` are routed through `run_command`. If an unrecognized command is provided, it triggers `EVENT_COMMAND_STARTED`.
    - **Agent Mode:** When `/agent` is invoked, the chat enters a state where the next input is treated as a task description, combined with any staged files, and dispatched via `EVENT_AGENT_RUN_REQUESTED`.
- **Side Effects:** 
    - **Filesystem Access:** Reads files from the local disk when the `@` prefix is used.
    - **Terminal I/O:** Heavily manipulates the terminal via `prompt_toolkit`, including the use of a bottom toolbar for status updates and ANSI color formatting for text.
- **Error Handling:** 
    - File reading errors (e.g., `PermissionError`) are caught and reported to the user via formatted console output rather than crashing the loop.
    - `KeyboardInterrupt` and `EOFError` are caught to trigger a graceful `terminate_chat()`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables are explicitly required by this module, though it relies on the terminal's TTY state for `prompt_toolkit` behavior.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `datetime`, `typing`, `prompt_toolkit`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.core.events](/AgentDocs/ai/core/events.md)
    - [ai.color](/AgentDocs/ai/color.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)