## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | SessionManager |
| Source file | session_manager.py |

The **SessionManager** serves as the temporal orchestrator for the application's execution context. Its primary purpose is to manage the lifecycle of session identifiers and the physical file system structure required to persist chat histories, thinking logs, and error reports. By providing a unified way to resolve session-specific paths, it ensures that data generated during a single interaction window is logically grouped and retrievable.

**Functional Mission**
The core mission of **SessionManager** is to implement a "warm-start" persistence mechanism. It solves the problem of session fragmentation during rapid sequential executions by attempting to resume a recent session (within a 5-minute window) rather than generating a new timestamped identity for every invocation. This ensures continuity in logging and workspace management for high-frequency automated calls.

**System Context & Integration**
This component acts as a foundational service that prepares the environment for downstream modules. It populates global state variables within [ai.functions](/docs/ai/functions.md) to direct where logs and errors are written. It relies heavily on [ProgramConfig](/docs/ai/services/config_helper.md) to resolve base directory paths and provides the necessary file paths to modules responsible for chat management and LLM reasoning.

- **INTERNAL REFERENCES**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `config.get(ProgramSetting.PATHS_LOGS)`  Retrieves the base directory for all system logs.
- `config.get(ProgramSetting.PATHS_CHAT_LOG)`  Retrieves the directory dedicated to JSON chat history files.

**Hardcoded Constants:**
- `300` (Default: `300`)  The "warm session" threshold in seconds (5 minutes) used to determine if a previous session should be resumed.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `initialize_session_paths` | Static Method | Orchestrates session ID determination, directory creation, and path mapping for logs, chat, and workspaces. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Locates the `last_session.id` pointer in the logs directory.
    - Checks the file modification time of the pointer.
- **Data Path**: 
    - **Input**: `ProgramConfig` object containing path settings.
    - **Processing**: 
        1. **Persistence Check**: If `last_session.id` exists and is < 300s old, `session_timestamp` is set to the existing ID.
        2. **New Session Creation**: If no warm session is found, a new `YYYYMMDD_HHMMSS` timestamp is generated and written to the pointer file.
        3. **Path Construction**: Builds absolute paths for chat logs, thinking logs, and error logs using the determined timestamp.
        4. **Global State Update**: Overwrites `func.ACTIVE_ERROR_FILENAME`, `func.SESSION_ERROR_FILENAME`, `func.ACTIVE_LOG_FILENAME`, and `func.SESSION_LOG_FILENAME`.
    - **Output**: A dictionary (`session_paths`) containing the resolved `session_timestamp` and all specific file paths.
- **Conditional Branching**:
    - **Warm vs. Cold Start**: Decides whether to reuse an existing ID or generate a new one based on file age.
    - **Config Availability**: Checks if `chat_log_folder` is configured; if not, logs a warning and sets the path to `None`.
    - **Directory Existence**: Uses `ensure_directory_exists` and `os.makedirs` to guarantee the physical existence of log subdirectories before returning paths.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `datetime`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)
- **External Packages**: None identified.