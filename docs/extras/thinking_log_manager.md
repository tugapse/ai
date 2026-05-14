## 1. Architectural Role
Provides thread-safe, file-based logging for "thinking" process content by managing synchronized access to both specific session logs and a global active log file.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Orchestrates log file creation, directory management, and synchronized write operations. |
| `__init__` | Method | Initializes file paths, sanitizes filenames, establishes directory structures, and sets lock parameters. |
| `_acquire_write_lock` | Method | Implements a polling-based file lock mechanism using `os.O_EXCL` to prevent concurrent write collisions. |
| `_release_write_lock` | Method | Removes the `.lock` file to permit subsequent write operations. |
| `write_thinking_log` | Method | Appends content to both the specific `log_file_path` and the `_default_log_filename` under lock protection. |
| `write_session_header` | Method | Prepends a timestamped header to the specific log (append mode) and overwrites the active log (write mode). |
| `read_thinking_log` | Method | Retrieves the full string content of the specific `log_file_path`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Sets `max_lock_wait_time` and `lock_poll_interval`.
    2. Sanitizes `log_file_name` (replaces spaces with underscores, ensures `.log` extension).
    3. Resolves `base_log_dir` via `ProgramConfig.current` and `ProgramSetting.PATHS_LOGS`.
    4. Falls back to `os.path.expanduser("~")` + `DEFAULT_LOG_SUBDIR` if config is unavailable.
    5. Creates `self.log_dir` via `os.makedirs`.
    6. Computes `self.log_file_path`, `self._default_log_filename`, and `self.lock_file_path`.
- **Data Path**: 
    - **Input**: `content` (str) or `tags` (str).
    - **Processing**: Lock acquisition (polling loop) $\rightarrow$ File I/O (append/write) $\rightarrow$ Lock release.
    - **Output**: Persistent text data written to disk at `log_file_path` and `_default_log_filename`.
- **Conditional Branching**:
    - **Lock Acquisition**: If `os.open` fails with `errno.EEXIST`, enter a `while` loop until `max_lock_wait_time` is exceeded (raises `TimeoutError`) or lock is acquired.
    - **Config Availability**: Checks `ProgramConfig.current` to decide between user-defined log paths or home-directory defaults.
    - **File Existence**: `read_thinking_log` checks `os.path.exists` before attempting read operations.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `errno`, `datetime`
- **Internal Modules**: `config` (`ProgramConfig`, `ProgramSetting`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `DEFAULT_LOG_SUBDIR`: `"Ai/logs/thinking"`
    - `DEFAULT_FILENAME`: `"thinking_process.log"`
- **Environment Lookups**: 
    - `ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)`
    - `os.path.expanduser("~")`