## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| CommandExecutor | /ai/chat/command_executor.md |

This component provides the core abstraction for executing system commands, offering both synchronous and asynchronous execution patterns. Its primary responsibility is to manage the lifecycle of a command execution—from initiation to completion—and reliably pass the outcome (success or failure) to a registered callback mechanism.

This module functions as a critical service layer within the application architecture. It sits above the raw execution layer, providing a structured interface for command handling. The `AsyncExecutor` specifically implements the threading mechanism, allowing operations to proceed concurrently without blocking the main execution flow, which is essential for responsive chat services.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ExecutorResult | Class | Represents the outcome of a command execution, holding the result and any associated error. |
| CommandExecutor | Class | Base class defining the contract for executing commands, including `run()` and `output_requested()`. |
| AsyncExecutor | Class | Inherits from `CommandExecutor` to handle asynchronous execution via `threading.Thread`. |
| _trigger_callback | Method | Internal method used by executors to dispatch the final result to the registered `finished_callback`. |
| run | Method | Executes the command. For `CommandExecutor`, it raises `NotImplementedError`; for `AsyncExecutor`, it manages thread startup and joining. |
| output_requested | Method | Checks if command output should be captured; raises `NotImplementedError` in base class. |
| terminate | Method | Sets the internal thread reference to None, effectively stopping the executor's thread tracking. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `CommandExecutor` defines the interface. The `AsyncExecutor` implements this by launching the command execution logic (`_run_thread`) within a dedicated `threading.Thread`. The `_run_thread` method simulates command execution and then calls `_trigger_callback` upon completion, passing either the successful result or any caught exception.
- **Side Effects:** Spawns processes/threads (via `threading.Thread`) and invokes external callback functions (`finished_callback`).
- **Error Handling:** The base `CommandExecutor` enforces execution contracts by raising `NotImplementedError` for unimplemented methods. The `AsyncExecutor` uses a `try...except` block within `_run_thread` to catch any runtime exceptions during simulated execution and reports them via the callback.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `threading`
- **Internal:** None