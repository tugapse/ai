## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ProcessManager** | [src/ai/services/process_manager.py](/AgentDocs/ai/services/process_manager.md) |

The `ProcessManager` is responsible for managing the lifecycle and state persistence of a running process instance. Its primary role is to ensure process exclusivity, preventing multiple instances of the application from running simultaneously by utilizing file-based locking mechanisms.

Within the broader system architecture, this component serves as a low-level service that provides process identification and state synchronization. It utilizes `fcntl` for atomic file operations and relies on a `DirectoryManager` to resolve the appropriate filesystem locations for PID and lock files.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ProcessManager(directory_manager)` | Class | Initializes a new manager instance. Requires a [DirectoryManager](/AgentDocs/ai/services/directory_manager.md) for filesystem operations. |
| `is_process_running(pid)` | Static Method | Returns `True` if a process with the specified PID is active, `False` otherwise. |
| `get_current_process_id()` | Static Method | Returns the integer PID of the current execution context. |
| `set_state(key, value)` | Static Method | Updates the internal `_state` dictionary and triggers a persistent save if an active instance exists. |
| `save()` | Static Method | Serializes the current `_state` to disk via the active instance. Throws [func.Error](/AgentDocs/ai/functions.md) if no instance is found. |
| `write(content)` | Method | Performs an atomic write of serialized content to the PID file, ensuring the file is truncated and synced to disk. |
| `start()` | Method | Attempts to acquire an exclusive non-blocking lock on the PID file. Raises `RuntimeError` if the process is already running. |
| `shutdown()` | Method | Releases the file lock, closes the file handle, and removes the PID file from the filesystem. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class implements a Singleton-like pattern for state management via the `_instance` class variable. It uses `fcntl.flock` with `LOCK_EX | LOCK_NB` to implement a non-blocking exclusive lock. This ensures that if a second instance attempts to `start()`, it will immediately encounter a `BlockingIOError`, which is then re-raised as a `RuntimeError`.
- **Side Effects:** 
    - **Filesystem:** Creates directories, writes PID files, performs file truncation, and deletes files during `shutdown()`.
    - **Process Signaling:** Uses `os.kill(pid, 0)` to probe for process existence.
    - **State Mutation:** Mutates the class-level `_state` dictionary.
- **Error Handling:** 
    - Throws `RuntimeError` if `write()` is called without an active lock or if `start()` fails due to an existing lock.
    - Uses [func.error](/AgentDocs/ai/functions.md) to handle failures during the `save()` operation when no instance is initialized.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `fcntl`, `json`.
- **Internal:** 
    - [DirectoryManager](/AgentDocs/ai/services/directory_manager.md)
    - [ai.functions](/AgentDocs/ai/functions.md)