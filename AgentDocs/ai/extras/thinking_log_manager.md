## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ThinkingLogManager** | [src/ai/extras/thinking_log_manager.py](/src/ai/extras/thinking_log_manager.py) |

The `ThinkingLogManager` is a specialized utility designed to capture and persist the internal "thought processes" of the AI. It provides a structured way to record the reasoning steps, intermediate logic, and metadata generated during agent operations, ensuring that these transient cognitive traces are preserved for debugging, auditing, or session reconstruction.

This component acts as a filesystem-based logging service within the broader application architecture. It integrates with the system's directory management logic to ensure logs are stored in appropriate locations and implements a custom file-locking mechanism to maintain data integrity during concurrent write operations.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | Manages lifecycle, writing, and reading of AI thinking logs with thread-safe file locking. |
| `ThinkingLogManager(log_file_name=None, max_lock_wait_time=10, lock_poll_interval=0.1)` | Constructor | Initializes the manager with an optional custom filename and configurable lock timeout/polling settings. |
| `write_thinking_log(content: str)` | Method | Appends string content to both the specific log file and the global active session log. |
| `write_session_header(tags: str = "")` | Method | Writes a timestamped session header to the specific log file and overwrites the active session log with the new header. |
| `read_thinking_log() -> str` | Method | Retrieves the full text content of the specific thinking log file. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class implements a primitive advisory locking mechanism using `os.open` with `O_CREAT | O_EXCL`. This ensures that only one process/thread can write to the log files at a time. If a lock file (`.lock`) exists, the manager polls at a defined interval until the lock is released or a timeout occurs.
- **Side Effects:** 
    - **Filesystem:** Creates directories via `os.makedirs`, creates/appends to `.log` files, and creates/deletes `.lock` files.
    - **I/O:** Performs synchronous file writes and reads.
- **Error Handling:** 
    - Throws `TimeoutError` if a file lock cannot be acquired within the `max_lock_wait_time`.
    - Throws `IOError` for general filesystem failures during locking.
    - Catches `TimeoutError` and `IOError` during write operations to prevent log failures from crashing the main AI execution flow, printing an error message to stdout instead.
    - Returns an empty string in `read_thinking_log` if the file is missing or unreadable.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are consumed; configuration is derived from the filesystem and initialized via class arguments.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `errno`, `datetime`.
- **Internal:** 
    - [ProgramConfig](/AgentDocs/ai/config.md)
    - [ProgramSetting](/AgentDocs/ai/config.md)
    - [DirectoryManager](/AgentDocs/ai/services/directory_manager.md)