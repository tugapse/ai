import pytest
from unittest.mock import Mock, MagicMock
import time
from threading import Event

from ai.chat.command_executor import ExecutorResult, CommandExecutor, AsyncExecutor

# Test for ExecutorResult
def test_executor_result_initialization():
    """
    Tests that ExecutorResult correctly stores the result and error.
    """
    result_data = {"status": "success"}
    error_data = ValueError("Test Error")

    # Test with result and no error
    res1 = ExecutorResult(result_data)
    assert res1.result == result_data
    assert res1.error is None

    # Test with result and error
    res2 = ExecutorResult(result_data, error_data)
    assert res2.result == result_data
    assert res2.error == error_data

# Tests for CommandExecutor
class TestCommandExecutor:
    def test_command_executor_initialization(self):
        """
        Tests that CommandExecutor initializes correctly.
        """
        mock_callback = Mock()
        command = "test_command"
        executor = CommandExecutor(command, mock_callback)
        assert executor._command_string == command
        assert executor.finished_callback == mock_callback

    def test_trigger_callback(self):
        """
        Tests that the _trigger_callback method calls the finished_callback
        with an ExecutorResult instance.
        """
        mock_callback = Mock()
        executor = CommandExecutor("test", mock_callback)
        result_data = "success"
        error_data = Exception("failure")

        # Test with result and no error
        executor._trigger_callback(result_data)
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0][0]
        assert isinstance(call_args, ExecutorResult)
        assert call_args.result == result_data
        assert call_args.error is None

        # Reset mock and test with error
        mock_callback.reset_mock()
        executor._trigger_callback(result_data, error_data)
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0][0]
        assert isinstance(call_args, ExecutorResult)
        assert call_args.result == result_data
        assert call_args.error == error_data

    def test_run_raises_not_implemented_error(self):
        """
        Tests that the base run() method raises NotImplementedError.
        """
        executor = CommandExecutor("test", Mock())
        with pytest.raises(NotImplementedError, match="Hey, don't forget to implement the run"):
            executor.run()

    def test_output_requested_raises_not_implemented_error(self):
        """
        Tests that the base output_requested() method raises NotImplementedError.
        """
        executor = CommandExecutor("test", Mock())
        with pytest.raises(NotImplementedError, match="Hey, don't forget to implement the output_requested"):
            executor.output_requested()


# Tests for AsyncExecutor
class TestAsyncExecutor:
    def test_async_executor_initialization(self):
        """
        Tests that AsyncExecutor initializes correctly and inherits from CommandExecutor.
        """
        mock_callback = Mock()
        command = "async_test"
        executor = AsyncExecutor(command, mock_callback)
        assert executor._command_string == command
        assert executor.finished_callback == mock_callback
        assert executor.thread_name == "Async Executor"
        assert executor.thread is None

    def test_run_creates_and_starts_thread(self, monkeypatch):
        """
        Tests that run() creates a thread, sets its name, and starts it.
        """
        mock_thread = MagicMock()
        # When Thread is instantiated, return our mock, accepting any arguments
        monkeypatch.setattr('ai.chat.command_executor.Thread', lambda **kwargs: mock_thread)

        mock_callback = Mock()
        executor = AsyncExecutor("async_test", mock_callback)

        executor.run(auto_start=True, wait=False)

        assert mock_thread.name == "Async Executor"
        mock_thread.start.assert_called_once()
        assert executor.thread == mock_thread

    def test_run_with_wait(self, monkeypatch):
        """
        Tests that run() with wait=True calls join() on the thread.
        """
        mock_thread = MagicMock()
        monkeypatch.setattr('ai.chat.command_executor.Thread', lambda **kwargs: mock_thread)

        mock_callback = Mock()
        executor = AsyncExecutor("async_test", mock_callback)

        executor.run(auto_start=True, wait=True)

        mock_thread.start.assert_called_once()
        mock_thread.join.assert_called_once()

    def test_terminate(self, monkeypatch):
        """
        Tests that terminate() sets the thread to None.
        """
        mock_thread = MagicMock()
        monkeypatch.setattr('ai.chat.command_executor.Thread', lambda **kwargs: mock_thread)

        executor = AsyncExecutor("test", Mock())
        # Simulate that a thread has been created
        executor.run(auto_start=False)
        assert executor.thread is not None
        executor.terminate()
        assert executor.thread is None

    def test_run_thread_success_triggers_callback(self):
        """
        Tests that _run_thread calls _trigger_callback with a result on success.
        """
        executor = AsyncExecutor("test_command", Mock())
        executor._trigger_callback = Mock()  # Spy on the method

        executor._run_thread()

        executor._trigger_callback.assert_called_once_with(
            "Successfully executed: test_command"
        )

    def test_run_thread_exception_triggers_callback(self):
        """
        Tests that the except block in _run_thread correctly calls the callback with an error.
        """
        test_exception = ValueError("Simulated failure")
        final_callback = Mock()
        executor = AsyncExecutor("test_command", final_callback)

        # Keep a reference to the original method to call it from our mock
        original_trigger = executor._trigger_callback
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise test_exception
            else:
                # On the second call (from the except block), invoke the original logic
                return original_trigger(*args, **kwargs)

        executor._trigger_callback = Mock(side_effect=side_effect)

        executor._run_thread()
        
        # The mock should have been called twice (once in try, once in except)
        assert executor._trigger_callback.call_count == 2
        
        # The final callback (passed at initialization) should be called once with the error
        final_callback.assert_called_once()
        result_arg = final_callback.call_args[0][0]
        assert isinstance(result_arg, ExecutorResult)
        assert result_arg.result is None
        assert result_arg.error == test_exception

    def test_run_without_autostart(self, monkeypatch):
        """
        Tests that run(auto_start=False) creates a thread but does not start it.
        """
        mock_thread = MagicMock()
        monkeypatch.setattr('ai.chat.command_executor.Thread', lambda **kwargs: mock_thread)

        mock_callback = Mock()
        executor = AsyncExecutor("async_test", mock_callback)

        executor.run(auto_start=False)

        assert executor.thread == mock_thread
        mock_thread.start.assert_not_called()

    def test_terminate_before_run(self):
        """
        Tests that calling terminate() before run() is safe.
        """
        executor = AsyncExecutor("test", Mock())
        # Should not raise any error
        executor.terminate()
        assert executor.thread is None

    def test_output_requested_raises_not_implemented_error(self):
        """
        Tests that the inherited output_requested() method raises NotImplementedError.
        """
        executor = AsyncExecutor("test", Mock())
        with pytest.raises(NotImplementedError, match="Hey, don't forget to implement the output_requested"):
            executor.output_requested()

    def test_terminate_does_not_stop_thread(self):
        """
        Tests that terminate() only nullifies the thread reference and does not
        actually stop the thread, which could be running a long task.
        """
        can_finish = Event()
        
        executor = AsyncExecutor("long_task", Mock())

        def long_running_task_replacement():
            """A task that waits for an event before finishing."""
            # This replaces _run_thread
            can_finish.wait()

        # Replace the _run_thread method with our waiting function
        executor._run_thread = long_running_task_replacement
        
        # Run the executor, which will start the thread with our replacement method
        executor.run(auto_start=True, wait=False)
        
        # Keep a reference to the actual thread object
        original_thread_ref = executor.thread
        
        # Give the thread a moment to start and enter the wait()
        time.sleep(0.1)
        assert original_thread_ref is not None
        assert original_thread_ref.is_alive()

        # Now, terminate the executor
        executor.terminate()

        # The executor's reference is gone
        assert executor.thread is None
        
        # But the original thread is still running because it's stuck in wait()
        assert original_thread_ref.is_alive()

        # Cleanup: signal the thread to finish and join it
        can_finish.set()
        original_thread_ref.join(timeout=1) # Use a timeout for safety
        
        assert not original_thread_ref.is_alive()

    def test_run_called_multiple_times(self, monkeypatch):
        """
        Tests that calling run() multiple times creates a new thread each time,
        replacing the previous one on the executor instance.
        """
        # Using a list to store the created mock threads
        created_threads = []
        def mock_thread_factory(**kwargs):
            mock = MagicMock()
            created_threads.append(mock)
            return mock

        monkeypatch.setattr('ai.chat.command_executor.Thread', mock_thread_factory)

        executor = AsyncExecutor("test", Mock())

        # First call to run()
        executor.run(auto_start=False)
        assert len(created_threads) == 1
        first_thread = created_threads[0]
        assert executor.thread == first_thread

        # Second call to run()
        executor.run(auto_start=False)
        assert len(created_threads) == 2
        second_thread = created_threads[1]
        assert executor.thread == second_thread
        assert executor.thread != first_thread