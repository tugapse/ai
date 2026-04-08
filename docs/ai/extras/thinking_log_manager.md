## 1. Architectural Role
Manages a log file for "thinking" content, ensuring exclusive write access across processes using a simple lock file mechanism, while allowing concurrent reads.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Manages the creation, writing, and reading of a log file for "thinking" content, ensuring exclusive write access across processes. |
| `write_thinking_log` | Method | Writes content to the thinking log file. |
| `write_session_header` | Method | Writes a timestamped header to the log file. |
| `read_thinking_log` | Method | Reads the entire content of the thinking log file. |

## 3. Execution Logic & Flow
- **Initialization**:
  - The `ThinkingLogManager` class is initialized with default values for `log_file_name`, `max_lock_wait_time`, and `lock_poll_interval`.
  - The `log_file_name` is sanitized and extended with a `.log` extension if necessary.
  - The `log_dir` is determined based on `ProgramConfig` or a default path.
  - The `log_file_path` and `lock_file_path` are set.
  - The `log_dir` is created if it does not exist.

- **Data Path**:
  - `write_thinking_log`: Content is written to `log_file_path` and `_default_log_filename`.
  - `write_session_header`: A timestamped header is written to `log_file_path` and `_default_log_filename`.
  - `read_thinking_log`: The content of `log_file_path` is read.

- **Conditional Branching**:
  - `_acquire_write_lock`: Waits for a write lock by attempting to create a lock file. If the lock file already exists, it waits for a specified duration before timing out.
  - `_release_write_lock`: Deletes the lock file to release the write lock.
  - `write_thinking_log`: Handles exceptions related to lock acquisition and file operations.
  - `write_session_header`: Handles exceptions related to lock acquisition and file operations.
  - `read_thinking_log`: Waits briefly if a write lock is detected to minimize reading inconsistent data.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `time`, `errno`, `datetime`
- **Internal Modules**: `program` (for `ProgramConfig` and `ProgramSetting`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `DEFAULT_LOG_SUBDIR`
- **Environment Lookups**: `ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)`