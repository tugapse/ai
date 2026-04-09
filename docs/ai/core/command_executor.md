## 1. Architectural Role
The `command_executor.py` file defines a class `CommandExecutor` and its subclass `AsyncExecutor` for executing commands asynchronously.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `CommandExecutor` | Class | Provides a base class for executing commands and triggering callbacks upon completion. |
| `AsyncExecutor` | Class | Extends `CommandExecutor` to execute commands asynchronously in a separate thread. |
| `ExecutorResult` | Class | Represents the result of a command execution, containing the result and any error. |
| `run` | Method | Executes the command and triggers the callback. |
| `output_requested` | Method | Checks if output is requested for a command. |
| `terminate` | Method | Terminates the thread. |

## 3. Execution Logic & Flow
- **Initialization**:
  - `CommandExecutor`: Initializes with a command string and a finish callback.
  - `AsyncExecutor`: Inherits from `CommandExecutor` and adds a thread name and thread object.
- **Data Path**:
  - `CommandExecutor`: Receives a command and a callback, stores them, and raises `NotImplementedError` for `run` and `output_requested`.
  - `AsyncExecutor`: Inherits the command and callback, adds a thread name, and raises `NotImplementedError` for `run` and `output_requested`.
- **Conditional Branching**:
  - `AsyncExecutor.run`: Checks if `auto_start` is `True` and starts the thread if so. If `wait` is `True`, it waits for the thread to finish.

## 4. Resource Dependencies
- **Standard Libraries**: `threading`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None