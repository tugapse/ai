## 1. Architectural Role

**Functional Mission**
The **SessionManager** class is responsible for the lifecycle management of session-specific environments. Its primary mission is to provide temporal isolation for user interactions by generating unique session identifiers, establishing dedicated directory structures for chat histories, thinking logs, and workspaces, and implementing a "warm start" mechanism to persist session continuity during rapid sequential executions.

**System Context & Integration**
This component acts as a foundational utility that prepares the filesystem state required for downstream modules to operate within a scoped context. It integrates closely with [ProgramConfig](/docs/services/config_helper.md) to resolve system paths and utilizes [functions](/docs/functions.md) for filesystem operations and logging. By establishing the `session_timestamp` and associated file paths, it provides the necessary environmental metadata that subsequent modules (such as chat handlers or LLM orchestrators) use to ensure data persistence and traceability.

## 2. Environment & Configuration

**Environment Lookups:**
- `PATHS_LOGS` (via `config.get`)  Resolves the base directory for system logs and session pointers.
- `PATHS_CHAT_LOG` (via `config.get`)  Resolves the directory for storing JSON chat history files.
- `PATHS_WORKSPACES` (via `config.get`)  Resolves the base directory for session-specific working files.

**Hardcoded Constants:**
- `300` (Default: `300`)  The "warm session" threshold in seconds (5 minutes) used to determine if a previous session should be resumed.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionManager` | Class | Encapsulates logic for session lifecycle and path orchestration. |
| `initialize_session_paths` | Static Method | Orchestrates the detection of existing sessions, directory creation, and returns a dictionary of mapped session paths. |

## 4. Execution Logic & Flow

- **Initialization**: The method begins by retrieving the log directory from the configuration and locating the `last_session.id` pointer file.
- **Data Path**: 
    1. **Session Identification**: Reads `last_session.id` $\rightarrow$ Checks file modification time $\rightarrow$ If $< 300s$, adopts existing ID; else, generates new `YYYYMMDD_HHMMSS` timestamp.
    2. **Path Mapping**: Timestamp $\rightarrow$ Joins with configured/default paths for Chat Logs, Thinking Logs, and Workspaces.
    3. **Filesystem Provisioning**: Validates/creates directories for chat, thinking, and workspace paths.
    4. **Global State Update**: Updates `func.ACTIVE_LOG_FILENAME` and `func.SESSION_LOG_FILENAME` with the new session context.
- **Conditional Branching**:
    - **Warm vs. Cold Session**: If `session_id_pointer` exists and is recent, the logic bypasses new ID generation.
    - **Config Availability**: If `chat_log_folder` or `generated_files_base_path` are missing from config, the system falls back to default directory structures or issues warnings.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `time`, `datetime`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [ProgramConfig](/docs/services/config_helper.md)
    - [ProgramSetting](/docs/services/config_helper.md)
- **External Packages**: None identified.