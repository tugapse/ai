## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ThinkingLogManager | ai/extras/thinking_log_manager |

This component is responsible for managing persistent, structured logs related to the AI's internal "thinking" processes. Its primary duty is to provide robust, thread-safe mechanisms for writing thought content, marking session starts, and retrieving historical log data. It specifically addresses the need for reliable logging even in concurrent execution environments by implementing file locking.

Architecturally, `ThinkingLogManager` functions as a specialized logging service within the application's utility layer. It interfaces with the system's directory structure via [DirectoryManager](/ai/services/directory_manager.md) to ensure logs are placed in the correct system location. It coordinates writes to both a specific, user-defined log file and a designated active session log file.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Manages the creation, writing, and reading of logs related to the AI's internal thought processes. |
| `write_thinking_log` | Method | Writes the provided content to both the specific log file and the active session log. |
| `write_session_header` | Method | Writes a session start header to both the specific log file and the active session log. |
| `read_thinking_log` | Method | Reads and returns the entire content of the specific thinking log file. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses a file locking mechanism (implemented via `os.open` with `O_EXCL`) to ensure only one process can write to the log files at a time. Writing operations are atomic relative to other processes attempting to acquire the lock. It maintains two paths: a specific log path and a global active session log path.
- **Side Effects:** Reads and writes to the filesystem (creating directories, writing log files, removing lock files).
- **Error Handling:** `_acquire_write_lock` raises `TimeoutError` if the lock cannot be acquired within `max_lock_wait_time` or `IOError` for other file system issues. `write_thinking_log` and `write_session_header` catch these errors and print a warning instead of halting execution. `read_thinking_log` returns an empty string on any I/O error or if the file is absent.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `errno`, `datetime`
- **Internal:** [ProgramConfig](/ai/config.md), [ProgramSetting](/ai/config.md), [DirectoryManager](/ai/services/directory_manager.md)