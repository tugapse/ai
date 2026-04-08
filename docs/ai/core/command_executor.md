## Module Purpose
This module provides a command executor class that can be used to execute commands asynchronously. It defines an interface for command execution and an asynchronous implementation using threading.

## Interface & Exports
*   Class: `ExecutorResult`
*   Class: `CommandExecutor`
*   Class: `AsyncExecutor`

## Internal Logic
The file defines an `ExecutorResult` class to encapsulate the outcome of a command, including any errors. The `CommandExecutor` class serves as an abstract base for command execution, requiring subclasses to implement `run` and `output_requested` methods and providing a `_trigger_callback` mechanism. The `AsyncExecutor` class extends `CommandExecutor` to execute commands in a separate `threading.Thread`. Its `run` method creates and optionally starts and joins a thread, targeting an internal `_run_thread` method (which is not defined in this snippet but implied by its usage). It also includes a `terminate` method to clear the thread reference.

## Dependencies
*   `threading` (specifically `Thread`)

## Constants & Environment
*   `AsyncExecutor.thread_name`: `"Async Executor"`