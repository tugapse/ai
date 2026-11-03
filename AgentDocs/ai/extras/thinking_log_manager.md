## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ThinkingLogManager** | [src/ai/extras/thinking_log_manager.py](/AgentDocs/ai/extras/thinking_log_manager.md) |

The `ThinkingLogManager` is a specialized utility designed to capture, persist, and manage the internal "thought processes" of the AI. It provides a structured way to log the reasoning steps that occur between user input and final output, which is critical for debugging, auditing, and observing the agent's cognitive flow.

This component acts as a filesystem utility within the broader AI architecture. It ensures that thinking logs are stored in a dedicated directory structure and provides thread-safe writing capabilities through a file-locking mechanism, preventing data corruption when multiple processes or threads attempt to log reasoning simultaneously.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ThinkingLogManager` | Class | The primary controller for managing thinking log files. Supports custom filenames, lock timeouts, and poll intervals. |
| `write_thinking_log(content: str)` | Method | Appends a string of content to both the specific log file and the global active session log. |
| `write_session_header(tags: str = "")` | Method | Writes a timestamped session start header to the log files, optionally including metadata tags. |
| `read_thinking_log() -> str` | Method | Retrieves the full text content of the current thinking log file. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses a file-based locking mechanism (`.lock` files) to ensure exclusive write access. It utilizes `os.open` with `O_CREAT | O_EXCL` to atomically create lock files. If a lock is held by another process, the manager enters a polling loop until `max_lock_wait_time` is reached.
- **Side Effects:** 
    - **Filesystem:** Creates directories and files within the system log path. It writes to two locations: a specific log file (e.g., `thinking_process.log`) and a shared `active_thinking_process.log`.
    - **I/O:** Performs blocking file I/O operations during write and read cycles.
- **Error Handling:** 
    - Throws `TimeoutError` if a file lock cannot be acquired within the configured duration.
    - Throws `IOError` for unexpected filesystem failures.
    - Internal `write` methods catch these errors and print a warning to the console to prevent the main AI execution loop from crashing due to logging failures.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required; however, the directory structure is determined by the system's log configuration via `DirectoryManager`.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `errno`, `datetime`.
- **Internal:** 
    - [ProgramConfig](/AgentDocs/ai/config.md)
    - [ProgramSetting](/AgentDocs/ai/config.md)
    - [DirectoryManager](/AgentDocs/ai/services/directory_manager.md)