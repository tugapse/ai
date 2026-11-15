## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Chat | /ai/chat/chat.md |

This component serves as the primary conversational interface for the AI application, managing the entire lifecycle of user interaction, from input reception to response delivery. Its core responsibility is to maintain the state of a dialogue, handle complex inputs like multi-line prompts and file attachments, and dispatch user requests to appropriate processing pipelines.

Architecturally, `Chat` acts as the main Controller/Session Manager. It integrates user input handling via `prompt_toolkit`, manages the conversation history (`self.messages`), and orchestrates workflows by triggering events like `EVENT_CHAT_SENT` or `EVENT_AGENT_RUN_REQUESTED` to other specialized services, such as those found in [ai.functions](/ai/functions.md) or [ai.core.events](/ai/core/events.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatRoles` | Class | Defines constants for roles used in chat messages (USER, ASSISTANT, SYSTEM, CONTROL, TOOL). |
| `PrefixCompleter` | Class | Provides custom autocompletion suggestions for commands (starting with '/') and file paths (starting with '@'). |
| `Chat` | Class | Manages the entire chat session, input loop, state, and event triggering. |
| `Chat.update_suggestions()` | Method | Dynamically updates the lists of available commands and agents used by `PrefixCompleter`. |
| `Chat.loop()` | Method | Enters the main execution loop, continuously processing user input until termination. |
| `Chat.send_chat()` | Method | Formats the user message (including pending files) and triggers the `chat_sent` event. |
| `Chat.run_command()` | Method | Executes predefined chat commands like `/clear` or initiates agent mode via `/agent`. |
| `Chat.terminate_chat()` | Method | Sets the termination flag to gracefully exit the main loop. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The system operates around a main `while` loop (`loop()`) that utilizes `prompt_toolkit` for interactive input. Input processing differentiates between standard chat messages, command execution (via `/`), agent task activation (via `/agent`), and file staging (via `@`). File attachments are staged in `self.pending_files` and merged into the final payload just before sending or executing a command.
- **Side Effects:** Reads from the filesystem when handling file attachments (`_handle_file_attachment`) by using `os.scandir` and `open()`. It also writes to `stdout` via `func.out` for immediate feedback.
- **Error Handling:** Catches `KeyboardInterrupt` and `EOFError` within the prompt loop to allow for clean termination (`terminate_chat`). File reading errors during attachment are caught and reported using `func.out`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `datetime`, `typing`, `prompt_toolkit`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.core.events](/ai/core/events.md), [ai.color](/ai/color.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md).