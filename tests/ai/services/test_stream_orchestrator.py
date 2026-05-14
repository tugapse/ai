import pytest
from unittest.mock import MagicMock, patch, call

from ai.services.stream_orchestrator import StreamOrchestrator, StreamResult

# Mock the 'functions' module, a common dependency
func = MagicMock()

# To use mocks for other modules, we patch them at the class level
@patch('ai.services.stream_orchestrator.SpeechBridge')
@patch('ai.services.stream_orchestrator.func', func)
class TestStreamOrchestrator:

    def setup_method(self):
        """Set up mocks for each test."""
        func.reset_mock()

        # Mock dependencies passed to the constructor
        self.mock_voice_module = MagicMock()
        self.mock_output_printer = MagicMock()
        self.mock_handler_manager = MagicMock()
        self.mock_token_processor = MagicMock()
        
        # This will be the mock for the SpeechBridge instance.
        # The class-level patch will give us a mock class that we configure
        # in each test to return this instance.
        self.mock_speech_bridge_instance = MagicMock()

        # --- Configure mock behaviors ---
        # The printer just returns the token it was given
        self.mock_output_printer.process_token.side_effect = lambda token: token
        # The handler manager returns a tuple indicating to display the content
        self.mock_handler_manager.process_token_chain.side_effect = lambda token: (True, token, None)
        # The token processor just returns the content it was given
        self.mock_token_processor.process_token.side_effect = lambda content: content



    def test_run_with_keyboard_interrupt(self, mock_speech_bridge_class):
        """Tests that a KeyboardInterrupt is handled gracefully."""
        # Arrange
        mock_speech_bridge_class.return_value = self.mock_speech_bridge_instance
        
        orchestrator = StreamOrchestrator(
            voice_module=self.mock_voice_module,
            output_printer=self.mock_output_printer,
            handler_manager=self.mock_handler_manager,
            token_processor=self.mock_token_processor,
            debug_voice=False
        )

        def faulty_generator():
            yield "start"
            raise KeyboardInterrupt
            yield "end" # This should not be reached

        # Act: Run the orchestrator
        result = orchestrator.run(faulty_generator())

        # Assert: Check for interruption signal and partial text
        assert result.accumulated_text == "start"
        assert result.interrupted
        
        # Verify the speech bridge was aborted
        self.mock_speech_bridge_instance.abort.assert_called_once()
        self.mock_speech_bridge_instance.flush.assert_not_called() # Abort is called instead

   

    def test_run_with_printer_flush(self, mock_speech_bridge_class):
        """Tests that the printer's flush buffer is processed at the end."""
        # Arrange
        mock_speech_bridge_class.return_value = self.mock_speech_bridge_instance
        
        orchestrator = StreamOrchestrator(
            voice_module=self.mock_voice_module,
            output_printer=self.mock_output_printer,
            handler_manager=self.mock_handler_manager,
            token_processor=self.mock_token_processor,
            debug_voice=False
        )

        def stream_generator():
            yield "Final"

        # Configure the printer mock to have a flush method that returns a final chunk
        self.mock_output_printer.flush = MagicMock(return_value="...flushed!")

        # Act
        result = orchestrator.run(stream_generator())

        # Assert
        assert result.accumulated_text == "Final...flushed!"
        self.mock_output_printer.flush.assert_called_once()
        # Check that the flushed content was also displayed and spoken
        func.out.assert_has_calls([
            call("Final", end="", flush=True),
            call("...flushed!", end="", flush=True)
        ])
        self.mock_speech_bridge_instance.feed.assert_has_calls([
            call("Final"),
            call("...flushed!")
        ])