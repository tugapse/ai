## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **SessionManager** | [src/ai/services/session_manager.py](/src/ai/services/session_manager.py) |

The `SessionManager` is responsible for managing session-specific lifecycles, specifically the generation and persistence of session identifiers, timestamps, and associated file paths. It provides a mechanism to ensure that rapid sequential calls to the system can resume a "warm" session (defined as a session started within the last 5 minutes) rather than creating redundant new sessions.

In the broader application architecture, this component acts as a service layer utility that coordinates filesystem organization for logs and workspaces. It ensures that chat histories, LLM thinking logs, and error logs are consistently mapped to a specific temporal session ID, facilitating organized debugging and state persistence.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `SessionManager` | Class | A utility class containing static methods for managing session state and filesystem paths. |
| `initialize_session_paths(config: ProgramConfig)` | Static Method | Generates a session ID (either by resuming a warm session or creating a new one) and returns a dictionary containing paths for chat logs, thinking logs, and workspace directories. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class implements a two-stage persistence check. It first looks for a `last_session.id` file within the system logs directory. If the file exists and its modification time is less than 300 seconds (5 minutes) old, the existing ID is reused. Otherwise, a new timestamp-based ID is generated using `datetime.now()`.
- **Side Effects:** 
    - **Filesystem Writes:** Creates/updates `last_session.id` in the logs directory.
    - **Directory Creation:** Ensures existence of `chat` and `thinking` subdirectories within the logs path.
    - **Global State Mutation:** Updates global variables within the `ai.functions` module, specifically `ACTIVE_ERROR_FILENAME`, `SESSION_ERROR_FILENAME`, `ACTIVE_LOG_FILENAME`, and `SESSION_LOG_FILENAME`.
    - **Filesystem Creation:** Creates a `logs` subdirectory to house session-specific error and log files.
- **Error Handling:** If the chat log path is not successfully retrieved via the directory manager, it logs a warning using `func.log` but continues execution.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Used to retrieve application settings, although much of the directory logic is currently delegated to the `DirectoryManager`.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `datetime`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.config_helper](/AgentDocs/ai/services/config_helper.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)