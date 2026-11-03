## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Chat Engine** | [src/ai/chat/chat.py](/AgentDocs/ai/chat/chat.md) |

The `Chat` component serves as the primary interactive interface for the user, managing the lifecycle of a conversational session. It handles real-time user input via a terminal-based prompt, manages conversational state (including message history and pending file attachments), and orchestrates the transition between standard chat modes and specialized "Agent" task modes.

This component acts as a controller within the application architecture, bridging the gap between raw user input and the underlying AI logic. It utilizes an event-driven model (extending [src/ai/core/events.py](/AgentDocs/ai/core/events.md)) to signal when messages are sent, commands are executed, or agent tasks are requested, allowing other system modules to react to user interactions without tight coupling.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatRoles` | Class | A constant provider defining standard roles: `USER`, `ASSISTANT`, `SYSTEM`, `CONTROL`, and `TOOL`. |
| `PrefixCompleter` | Class | A custom `prompt_toolkit` completer that provides command suggestions (via `/`) and file path completions (via `@`). |
| `Chat` | Class | The main session manager for user interaction. |
| `Chat.loop()` | Method | Starts the blocking main execution loop for the chat interface. |
| `Chat.update_suggestions()` | Method | Dynamically updates the available command and agent lists for the completer. |
| `Chat.send_chat(message_content)` | Method | Dispatches a user message to the system and triggers the `EVENT_CHAT_SENT` event. |
| `Chat.run_command(message)` | Method | Processes slash-commands (e.g., `/clear`, `/agent`) to modify session state. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component implements a stateful loop using `prompt_toolkit`. It supports "Deferred File Attachment," where files prefixed with `@` are staged in a `pending_files` dictionary and automatically injected into the context of the subsequent text message or agent task. It also manages a "Multiline Mode" toggled via keyboard shortcuts to allow complex user inputs.
- **Side Effects:** 
    - **Filesystem:** Reads files from the local filesystem when the `@` prefix is used for attachment.
    - **Console I/O:** Directly manipulates the terminal output using ANSI colors and `prompt_toolkit`'s bottom toolbar and prompt formatting.
    - **State Mutation:** Maintains an internal list of `messages` which is subject to a maximum size limit (`max_chat_log`) to prevent memory exhaustion.
- **Error Handling:** 
    - Catches `PermissionError` during file scanning in the `PrefixCompleter`.
    - Catches `KeyboardInterrupt` and `EOFError` to perform a graceful `terminate_chat()`.
    - Handles file reading errors by reporting them via [src/ai/functions.py](/AgentDocs/ai/functions.md).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `datetime`, `typing`, `prompt_toolkit`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.core.events](/AgentDocs/ai/core/events.md)
    - [ai.color](/AgentDocs/ai/color.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)