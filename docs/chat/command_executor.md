## 1. Architectural Role
Provides an abstract and asynchronous framework for executing command strings via callback-driven lifecycle management.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ExecutorResult` | Class | Data container for command outcomes, encapsulating `result` and `error`. |
| `CommandExecutor` | Class | Abstract base class defining the interface for command execution and callback triggering. |
| `CommandExecutor.__init__` | Method | Initializes the executor with a `command` string and a `finish_callback`. |
| `CommandExecutor._trigger_callback` | Method | Wraps `result` and `error` into an `ExecutorResult` and invokes `finished_callback`. |
| `CommandExecutor.run` | Method | Abstract method intended to execute the command; raises `NotImplementedError`. |
| `CommandExecutor.output_requested` | Method | Abstract method to check if output is required; raises `NotImplementedError`. |
| `AsyncExecutor` | Class | Concrete implementation of `CommandExecutor` that offloads execution to a background thread. |
| `AsyncExecutor.__init__` | Method | Initializes `AsyncExecutor` with base parameters and sets `thread_name` to "Async Executor". |
| `AsyncExecutor.run` | Method | Spawns a `Thread` targeting `_run_thread`; supports `auto_start` and `wait` (join) logic. |
| `AsyncExecutor._run_thread` | Method | Internal thread target; simulates command execution and handles exception catching for the callback. |
| `AsyncExecutor.terminate` | Method | Nullifies the `thread` reference. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `CommandExecutor` instance is created with a specific command string and a callback function.
    - `AsyncExecutor` instance extends this by initializing a `thread_name` and a `thread` pointer set to `None`.
- **Data Path**: 
    - **Input**: A command string is passed during instantiation.
    - **Processing**: `AsyncExecutor.run` instantiates a `threading.Thread`. The `_run_thread` method executes, simulating a result string based on `self._command_string`.
    - **Output**: The resulting string (or an `Exception`) is encapsulated in an `ExecutorResult` object and passed to `self.finished_callback`.
- **Conditional Branching**:
    - **`AsyncExecutor.run`**: 
        - If `auto_start` is `False`, the method returns immediately without spawning a thread.
        - If `wait` is `True`, the calling thread blocks on `self.thread.join()`.
    - **`AsyncExecutor._run_thread`**: 
        - `try` block: Executes successful simulation and triggers callback with `result`.
        - `except` block: Catches any `Exception` and triggers callback with `None` and the `error` object.

## 4. Resource Dependencies
- **Standard Libraries**: `threading.Thread`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `thread_name = "Async Executor"`
    - Simulated success message format: `"Successfully executed: {self._command_string}"`