from threading import Thread

"""
This module provides a command executor class that can be used to execute commands asynchronously.
"""

class ExecutorResult:
    """
    This class represents the result of an executed command.

    Attributes:
        result (any): The result of the command execution.
        error (Exception, optional): An exception raised during command execution. Defaults to None.
    """

    def __init__(self, result, error=None) -> None:
        self.result = result
        self.error = error


class CommandExecutor:
    """
    This class represents a command executor that can be used to execute commands.

    Attributes:
        _command_string (str): The command string to be executed.
        finished_callback (callable): A callback function to be called when the command execution is finished.
    """

    def __init__(self, command, finish_callback) -> None:
        self._command_string = command
        self.finished_callback = finish_callback

    """
    Trigger the finished callback with the result and error.

    Args:
        result (any): The result of the command execution.
        error (Exception, optional): An exception raised during command execution. Defaults to None.
    """

    def _trigger_callback(self, result, error=None):
        self.finished_callback(ExecutorResult(result, error))

    """
    Execute a command.

    Args:
        *args: Variable-length argument list.
        **kwargs: Keyword arguments.

    Raises:
        NotImplementedError: This method must be implemented by subclasses.
    """

    def run(self, *args, **kargs):
        raise NotImplementedError("Hey, don't forget to implement the run")

    """
    Check if output is requested for a command.

    Raises:
        NotImplementedError: This method must be implemented by subclasses.
    """

    def output_requested(self):
        raise NotImplementedError("Hey, don't forget to implement the run")


class AsyncExecutor(CommandExecutor):
    """
    This class represents an asynchronous command executor that can be used to execute commands asynchronously.

    Attributes:
        thread_name (str): The name of the thread for this executor.
        thread (Thread): The thread object for this executor.
    """

    def __init__(self, command, finish_callback) -> None:
        super().__init__(command, finish_callback)
        self.thread_name = "Async Executor"
        self.thread = None

    """
    Run the command in a separate thread.

    Args:
        auto_start (bool): Whether to start the thread automatically. Defaults to True.
        wait (bool): Whether to wait for the thread to finish. Defaults to False.
        *args: Variable-length argument list.
        **kwargs: Keyword arguments.
    """

    def run(self, auto_start=True, wait=False, **kargs):
        self.thread = Thread(target=self._run_thread)
        self.thread.setName(self.thread_name)

        if not auto_start:
            return

        self.thread.start()
        if wait:
            self.thread.join()

    """
    Terminate the thread.
    """

    def terminate(self):
        self.thread = None