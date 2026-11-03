## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ChatCommandInterceptor** | [src/ai/chat/chat_command_interceptor.py](/AgentDocs/ai/chat/chat_command_interceptor.md) |

The `ChatCommandInterceptor` class is responsible for monitoring chat input and intercepting specific command strings before they are processed as standard conversational text. It provides a mechanism to trigger administrative or session-management actions, such as saving, loading, or listing chat history.

This component acts as a controller within the chat subsystem. It attaches itself to a [Chat](/AgentDocs/ai/chat/chat.md) instance by subscribing to the `EVENT_COMMAND_STARTED` event. By intercepting these events, it can divert the execution flow from the standard LLM processing loop to specific utility functions, effectively managing the state of the chat session via the filesystem.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatCommandInterceptor(chat: Chat, root_folder: str)` | Class | Initializes the interceptor, attaching it to the provided `Chat` instance and setting the directory for session storage. |
| `run(command_text: str)` | Method | The primary entry point for command processing. Parses the input string to identify built-in commands (`/save`, `/load`, `/list`) or custom commands in `extra_commands`. |
| `handle_extra_command(command: str)` | Method | A placeholder method intended for subclassing to implement custom command logic. Raises `NotImplementedError` if called directly. |
| `save_session(filename: str)` | Method | Serializes the current `chat.messages` to a JSON file within the `root_folder`. |
| `load_session(filename: str)` | Method | Deserializes a JSON file from the `root_folder` and populates `chat.messages`, then uses `ConsoleChatReader` to replay the history. |
| `list_sessions()` | Method | Scans the `root_folder` and outputs a list of available session files to the console. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The interceptor uses string splitting to isolate the command verb (the first word of the input). It performs a conditional check against a hardcoded list of system commands and a dynamic list of `extra_commands`. If a match is found, it executes the corresponding logic and calls `self.chat.terminate_command()` to prevent the command text from being sent to the LLM.
- **Side Effects:** 
    - **Filesystem:** Writes JSON files to the `root_folder` via `save_session` and reads them via `load_session`. It also creates the `root_folder` directory if it does not exist.
    - **Console I/O:** Outputs status messages (INFO, WARNING) and session lists to the terminal using [func.out](/AgentDocs/ai/functions.md) and [Color](/AgentDocs/ai/color.md).
- **Error Handling:** 
    - Throws `NotImplementedError` if `handle_extra_command` is invoked without being overridden.
    - Provides a warning via `func.out` if a requested session file does not exist during a `/load` attempt.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables are explicitly required by this component; however, the `root_folder` parameter dictates the filesystem path for all session persistence.

**Module Dependencies:**
- **Standard/External:** `json`, `os`
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.chat.Chat](/AgentDocs/ai/chat/chat.md)
    - [ai.color](/AgentDocs/ai/color.md)
    - `[ai.extras.ConsoleChatReader]` (Note: `ConsoleChatReader` is imported from `ai.extras` but not explicitly mapped in the provided manifest; it is used for session replay).