## 1. Architectural Role
Provides a thread-safe, file-based logging mechanism for capturing and persisting "thinking" process content to both session-specific and global active log files.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Orchestrates the creation, locking, and writing of thinking process logs. |
| `__init__` | Method | Initializes paths, sanitizes filenames, and ensures log directory existence. |
| `write_thinking_log` | Method | Appends content to both the session-specific log and the active global log. |
| `write_session_header` | Method | Writes a timestamped session start marker to logs (overwrites active log). |
| `read_thinking_log` | Method | Reads and returns the full content of the session-specific log file. |

## 3. Execution Logic & Flow
- **Initialization**:
    1. Resolve `log_file_name` (fallback to `DEFAULT_FILENAME`).
    2. Sanitize filename (replace spaces with underscores, ensure `.log` extension).
    3. Determine `log_dir` by checking `ProgramConfig.current` for `ProgramSetting.PATHS_LOGS`; fallback to `~/Ai/logs/thinking`.
    4. Create `log_dir` via `os.makedirs`.
    5. Construct `log_file_path`, `_default_log_filename` (active log), and `lock_file_path`.
- **Data Path**:
    - **Write**: `content` $\rightarrow$ `_acquire_write_lock()` $\rightarrow$ Append to `log_file_path` $\rightarrow$ Append to `_default_log_filename` $\rightarrow$ `_release_write_lock()`.
    - **Header**: `tags` $\rightarrow$ `_acquire_write_lock()` $\rightarrow$ Append to `log_file_path` $\rightarrow$ Overwrite `_default_log_filename` $\rightarrow$ `_release_write_lock()`.
    - **Read**: `log_file_path` $\rightarrow$ File Read $\rightarrow$ `str` output.
- **Conditional Branching**:
    - **Lock Acquisition**: If `os.open` fails with `errno.EEXIST`, the system polls every `lock_poll_interval` until `max_lock_wait_time` is exceeded, triggering a `TimeoutError`.
    - **Path Resolution**: If `ProgramConfig.current` is `None` or the specific setting is missing, the system defaults to the user's home directory.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `errno`, `datetime`
- **Internal Modules**: `config.ProgramConfig`, `config.ProgramSetting`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**:
    - `DEFAULT_LOG_SUBDIR`: `"Ai/logs/thinking"`
    - `DEFAULT_FILENAME`: `"thinking_process.log"`
    - `max_lock_wait_time`: `10` (default)
    - `lock_poll_interval`: `0.1` (default)
- **Environment Lookups**:
    - `ProgramConfig.current` $\rightarrow$ `ProgramSetting.PATHS_LOGS`