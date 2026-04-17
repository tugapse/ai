## 1. Architectural Role
Provides an abstract framework and a threaded implementation for executing commands asynchronously with a callback-based result notification system.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ExecutorResult` | Class | Data container for the `result` and optional `error` of a command execution. |
| `CommandExecutor` | Class | Abstract base class defining the interface for command execution and callback triggering. |
| `AsyncExecutor` | Class | Concrete implementation that executes the `_run_thread` logic within a `threading.Thread`. |
| `CommandExecutor._trigger_callback` | Method | Wraps execution output into an `ExecutorResult` and passes it to `finished_callback`. |
| `CommandExecutor.run` | Method | Abstract method to initiate command execution. |
| `CommandExecutor.output_requested` | Method | Abstract method to determine if the command requires output. |
| `AsyncExecutor.run` | Method | Manages `Thread` instantiation, naming, and optional synchronization (`join`). |
| `AsyncExecutor.terminate` | Method | Resets the `thread` reference to `None`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `CommandExecutor` stores the `command` string and the `finished_callback` function.
    - `AsyncExecutor` initializes the base class and sets a default `thread_name` ("Async Executor").
- **Data Path**: 
    - Input (`command`, `*args`, `**kargs`) $\rightarrow$ `AsyncExecutor.run()` $\rightarrow$ `threading.Thread` $\rightarrow$ `_run_thread` (internal target) $\rightarrow$ `_trigger_callback()` $\rightarrow$ `ExecutorResult` $\rightarrow$ `finished_callback()`.
- **Conditional Branching**:
    - **`auto_start`**: If `False` in `AsyncExecutor.run`, the thread is created but not started, returning control to the caller immediately.
    - **`wait`**: If `True` in `AsyncExecutor.run`, the calling thread blocks until the executor thread completes via `self.thread.join()`.

## 4. Resource Dependencies
- **Standard Libraries**: `threading.Thread`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `self.thread_name = "Async Executor"`