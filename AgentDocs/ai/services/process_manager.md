## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ProcessManager** | [src/ai/services/process_manager.py](/src/ai/services/process_manager.py) |

The `ProcessManager` class is responsible for managing the lifecycle, state persistence, and concurrency constraints of a running process instance. It ensures that only a single instance of the application can execute simultaneously by utilizing file-based locking mechanisms.

Within the broader system architecture, this component acts as a service layer utility that provides process identification and atomic state management. It prevents race conditions and overlapping executions by maintaining a PID file and a shared state dictionary that is synchronized to disk.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `is_process_running(pid)` | Static Method | Checks if a process with the specified PID is active using `os.kill(pid, 0)`. Returns `bool`. |
| `get_current_process_id()` | Static Method | Retrieves the PID of the current process via `os.getpid()`. Returns `int`. |
| `set_state(key, value)` | Static Method | Updates the internal `_state` dictionary and triggers a `save()` if an active instance exists. |
| `save()` | Static Method | Serializes the current `_state` to the filesystem via the active instance. Raises `func.Error` if no instance is found. |
| `__init__(directory_manager)` | Constructor | Initializes the manager with a `DirectoryManager` instance and sets the singleton `_instance`. |
| `write(content)` | Method | Performs an atomic write to the PID file, including `seek`, `truncate`, `flush`, and `fsync`. |
| `start()` | Method | Attempts to acquire an exclusive non-blocking lock on the PID file. Raises `RuntimeError` if the process is already running. |
| `shutdown()` | Method | Releases the file lock, closes the file handle, and removes the PID file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class implements a singleton-like pattern for managing process state. It uses `fcntl.flock` with `LOCK_EX | LOCK_NB` to attempt to acquire an exclusive lock on a file located in the directory provided by the `DirectoryManager`. If the lock is successfully acquired, the process ID is written to the file. State management is handled through a class-level `_state` dictionary which is converted to JSON and written to the locked file during `save()` operations.
- **Side Effects:** 
    - **Filesystem:** Creates directories, creates/writes to PID files, and deletes PID files.
    - **Process Signaling:** Uses `os.kill` to probe process existence.
    - **Synchronization:** Uses `os.fsync` to ensure data is physically written to the storage device.
- **Error Handling:** 
    - Throws `RuntimeError` if `write()` is called without an active lock or if `start()` fails due to an existing lock (`BlockingIOError`).
    - Throws `func.Error` (from `ai.functions`) if `save()` is called when no `ProcessManager` instance has been initialized.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `fcntl`, `json`.
- **Internal:** 
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)
    - [ai.functions](/AgentDocs/ai/functions.md)