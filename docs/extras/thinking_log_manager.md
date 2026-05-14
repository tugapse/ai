## 1. Architectural Role
`ThinkingLogManager` serves as a specialized file-system utility responsible for the persistent logging of internal model "thinking" processes. It provides thread-safe/process-safe write operations via a file-locking mechanism, maintaining both a specific session log and a global "active" log file. It interfaces with [config.md](config.md) to resolve directory paths and ensures that reasoning traces are preserved for debugging or user observation within the broader AI execution lifecycle.

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)`  Retrieves the base directory for system logs from the global configuration.

**Hardcoded Constants:**
- `DEFAULT_LOG_SUBDIR` (Default: `"Ai/logs/thinking"`)  Fallback relative path for log storage.
- `DEFAULT_FILENAME` (Default: `"thinking_process.log"`)  Fallback filename for individual session logs.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Manages lifecycle, locking, and I/O for thinking logs. |
| `write_thinking_log` | Method | Appends string content to both the session log and the active log file under lock. |
| `write_session_header` | Method | Injects a timestamped session delimiter; resets the active log file to start fresh. |
| `read_thinking_log` | Method | Returns the full content of the current session log as a string. |
| `_acquire_write_lock` | Method | Implements an atomic file-based lock using `os.O_EXCL`. |
| `_release_write_lock` | Method | Removes the `.lock` file to permit subsequent write access. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Sanitizes the provided filename (replaces spaces with underscores, ensures `.log` extension).
    2. Resolves the log directory by checking [config.md](config.md) via `ProgramConfig`.
    3. Falls back to `~/.local/share/Ai/logs/thinking` (or equivalent) if config is unavailable.
    4. Initializes file paths for the session log, the global active log, and the lock file.
- **Data Path**:
    1. **Input**: String `content` or `tags`.
    2. **Processing**: 
        - Attempt to acquire lock via `_acquire_write_lock` (polls until `max_lock_wait_time` is reached).
        - Format timestamp/header if applicable.
        - Perform atomic append operations.
    3. **Output**: Persistent updates to `.log` files on disk.
- **Conditional Branching**:
    - **Lock Contention**: If `errno.EE_EXIST` occurs, enter a sleep-loop until timeout or success.
    - **Config Availability**: If `ProgramConfig.current` is `None`, divert path construction to user home directory.
    - **File Existence**: `read_thinking_log` returns empty string if the file does not exist.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `errno`, `datetime`
- **Internal Modules**: 
    - [config.md](config.md)
- **External Packages**: None identified.