## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **SessionManager** | [src/ai/services/session_manager.py](/AgentDocs/ai/services/session_manager.md) |

The `SessionManager` is responsible for the lifecycle management of application sessions, specifically focusing on the generation and persistence of session-specific file paths and unique identifiers. It provides a mechanism to ensure that logs, chat histories, and "thinking" traces are organized into distinct, timestamped directories and files, preventing data collision between different execution runs.

This component acts as a foundational service within the application architecture, providing the necessary filesystem context for other services to record activity. It implements a "warm session" resumption logic, allowing the system to recover the same session ID if a new process is started within a 5-minute window of the previous session's last modification.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SessionManager.initialize_session_paths(config: ProgramConfig)` | Static Method | Generates a dictionary of session-specific paths (chat logs, thinking logs, etc.) and ensures required directories exist. It attempts to resume a session if a `last_session.id` file exists and is less than 300 seconds old. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses a two-stage persistence check. It first looks for a `last_session.id` file in the system logs directory. If the file's modification time is within 300 seconds (5 minutes), it reuses that timestamp as the current `session_timestamp`. Otherwise, it generates a new timestamp using the format `%Y%m%d_%H%M%S` and writes it to the pointer file. It then constructs absolute paths for chat history, thinking logs, and various error/log files.
- **Side Effects:** 
    - **Filesystem:** Creates directories via `os.makedirs` and `func.ensure_directory_exists`. Writes the session ID to `last_session.id`.
    - **Global State Mutation:** Mutates global variables within the `ai.functions` module, specifically updating `func.ACTIVE_ERROR_FILENAME`, `func.SESSION_ERROR_FILENAME`, `func.ACTIVE_LOG_FILENAME`, and `func.SESSION_LOG_FILENAME`.
- **Error Handling:** If the chat log path is not configured, it logs a warning via `func.log` but continues execution. It relies on `DirectoryManager` to provide valid base paths.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  An object passed to the initialization method containing application settings used to derive directory structures.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `datetime`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.config_helper](/AgentDocs/ai/services/config_helper.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)