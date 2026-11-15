## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ProcessManager | ai/services/process_manager.md |

This component is responsible for managing the lifecycle and state persistence of running JARVIS instances. It implements a robust mechanism using file locking (`fcntl.flock`) on PID files within a designated directory to ensure that only one active instance can control its state at any given time. It provides standardized methods for serializing, deserializing, and atomically writing process status information.

The `ProcessManager` acts as a critical service layer component within the application architecture. It interacts heavily with the file system via the provided [DirectoryManager](/ai/services/directory_manager.md) to locate and manage PID files. It allows other parts of the system to query the status of all running instances, making it a central registry for process discovery.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ProcessManager.is_process_running(pid)` | Static Method | Checks if a process with the given PID is currently running by sending signal 0. |
| `ProcessManager.get_current_process_id()` | Static Method | Retrieves the Process ID of the current running process. |
| `ProcessManager.serialize(state)` | Static Method | Renders a state dictionary into a formatted string of "key: value" lines according to defined field order. |
| `ProcessManager.parse(text)` | Static Method | Parses a "key: value" formatted string back into a state dictionary. |
| `ProcessManager.set_state(key, value)` | Static Method | Sets a specific status field and triggers a save if the current instance holds the lock. |
| `ProcessManager.list_instances(pid_directory)` | Static Method | Scans the PID directory, attempts to acquire shared locks, and returns a list of active instance states. |
| `ProcessManager.__init__(directory_manager)` | Constructor | Initializes the manager instance, setting up local state variables for tracking the process. |
| `ProcessManager.write(content)` | Method | Writes the serialized state content to the active PID file handle atomically. |
| `ProcessManager.start()` | Method | Registers the current process by acquiring an exclusive lock on its PID file and writing initial status. |
| `ProcessManager.shutdown()` | Method | Gracefully cleans up by removing the PID file and releasing the associated file lock. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The core logic revolves around acquiring and maintaining exclusive locks on files named `<pid>.pid`. When an instance starts, it locks the file, writes its state, and updates the global `_instance` reference. Other instances can acquire shared locks to read the state. Stale processes are detected when a lister successfully acquires a shared lock but finds the process ID is no longer running (`os.kill(pid, 0)` fails).
- **Side Effects:** This component extensively interacts with the filesystem (reading, writing, deleting PID files) and utilizes OS-level primitives for process management (locking, checking process existence via `os.kill`). It mutates the static internal state (`_state`, `_instance`).
- **Error Handling:** Catches `BlockingIOError` during lock acquisition, raising a `RuntimeError` if the process is already running. It handles `FileNotFoundError` during listing, treating it as a normal shutdown. It validates input keys against `ProcessManager.FIELDS` to raise `ValueError` upon invalid state updates.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `fcntl`, `datetime`, `pathlib`, `typing`
- **Internal:** [DirectoryManager](/ai/services/directory_manager.md), [ai.functions](/ai/functions.md)