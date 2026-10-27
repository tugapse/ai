## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ThinkingLogManager |
| Source file | thinking_log_manager.py |

The **ThinkingLogManager** serves as a specialized utility for persisting the internal reasoning processes (the "thinking" steps) of the AI during execution. It provides a structured way to capture non-output cognitive data, ensuring that the chain of thought is preserved for debugging, auditing, or user transparency without polluting the primary chat interface.

**Functional Mission**
The primary responsibility of **ThinkingLogManager** is to provide thread-safe, file-based logging for "thinking" content. It solves the problem of concurrent write access to log files through a custom file-based locking mechanism and manages two distinct log streams: a persistent historical log and a volatile "active" log that represents the current session's state.

**System Context & Integration**
This component acts as a sidecar logging utility. It integrates with the system configuration via [ProgramConfig](/docs/ai/config.md) to determine appropriate filesystem paths. While it does not drive the core logic of the AI, it is intended to be called by modules responsible for LLM interaction or agent reasoning to record their internal state transitions. It maintains a separation between long-term reasoning history and the immediate, active reasoning stream used for real-time monitoring.

- **INTERNAL REFERENCES**: [ProgramConfig](/docs/ai/config.md), [ProgramSetting](/docs/ai/config.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramConfig.get_current().get(ProgramSetting.PATHS_LOGS)`  Retrieves the base directory for all system logs to ensure consistent pathing.

**Hardcoded Constants:**
- `DEFAULT_LOG_SUBDIR` (Default: `os.path.join("Ai", "logs", "thinking")`)  Fallback directory structure if no configuration is found.
- `DEFAULT_FILENAME` (Default: `"thinking_process.log"`)  The default name for the historical thinking log.
- `max_lock_wait_time` (Default: `10`)  Maximum seconds to attempt acquiring a file lock before raising a `TimeoutError`.
- `lock_poll_interval` (Default: `0.1`)  Frequency in seconds for checking lock availability.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Orchestrates log file creation, directory management, and thread-safe writing. |
| `write_thinking_log` | Method | Appends content to both the historical log file and the active session log file. |
| `write_session_header` | Method | Writes a timestamped header to the historical log and overwrites the active session log with the new session start. |
| `read_thinking_log` | Method | Retrieves the full content of the historical thinking log as a string. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Sanitizes the provided `log_file_name` (replacing spaces with underscores and ensuring `.log` extension).
    2. Attempts to resolve the log directory via [ProgramConfig](/docs/ai/config.md).
    3. Falls back to the user's home directory if configuration is unavailable.
    4. Creates the target directory if it does not exist.
    5. Defines paths for the historical log, the active session log, and a `.lock` file.
- **Data Path**: 
    - **Input**: Raw string `content`.
    - **Processing**: 
        1. Attempt to acquire a file lock via `_acquire_write_lock`.
        2. Open file handles in append mode (`a`).
        3. Write content to `self.log_file_path`.
        4. Write content to `self._default_log_filename`.
    - **Output**: Persistent data written to the filesystem.
- **Conditional Branching**:
    - **Lock Acquisition**: If `os.open` fails with `EEXIST`, the system enters a polling loop until `max_lock_wait_time` is exceeded, at which point a `TimeoutError` is raised.
    - **Error Handling**: `write_thinking_log` and `write_session_header` catch `TimeoutError` and `IOError` to prevent the main application from crashing due to logging failures, printing a warning to the console instead.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `errno`, `datetime`
- **Internal Modules**: 
    - [ProgramConfig](/docs/ai/config.md)
    - [ProgramSetting](/docs/ai/config.md)
- **External Packages**: None identified.