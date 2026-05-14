from unittest.mock import MagicMock, call

# Imports adjusted for PYTHONPATH=src
from ai.services.event_binder import EventBinder
from core.llms.base_llm import BaseModel
from chat.chat import Chat


class TestEventBinder:

    def setup_method(self):
        """Set up mocks for each test."""
        self.mock_chat = MagicMock(spec=Chat)
        # Mock class attributes that the code under test uses
        self.mock_chat.EVENT_CHAT_SENT = "chat_sent"
        self.mock_chat.EVENT_OUTPUT_REQUESTED = "output_requested"
        
        self.mock_llm = MagicMock(spec=BaseModel)
        # Mock the class attribute used in the code
        BaseModel.STREAMING_FINISHED_EVENT = "streaming_finished"

        self.mock_start_chat_callback = MagicMock()
        self.mock_output_requested_callback = MagicMock()
        self.mock_llm_stream_finished_callback = MagicMock()

    def test_bind_core_events_with_llm(self):
        """
        Test that all core events are bound correctly when an LLM is provided.
        """
        # Act
        EventBinder.bind_core_events(
            chat=self.mock_chat,
            llm=self.mock_llm,
            start_chat_callback=self.mock_start_chat_callback,
            output_requested_callback=self.mock_output_requested_callback,
            llm_stream_finished_callback=self.mock_llm_stream_finished_callback
        )

        # Assert Chat events
        chat_calls = [
            call(event_name="chat_sent", listener=self.mock_start_chat_callback),
            call(event_name="output_requested", listener=self.mock_output_requested_callback)
        ]
        self.mock_chat.add_event.assert_has_calls(chat_calls, any_order=True)

        # Assert LLM event
        self.mock_llm.add_event.assert_called_once_with(
            event_name="streaming_finished",
            listener=self.mock_llm_stream_finished_callback
        )

    def test_bind_core_events_without_llm(self):
        """
        Test that binding proceeds without error and only binds chat events when LLM is None.
        """
        # Act
        EventBinder.bind_core_events(
            chat=self.mock_chat,
            llm=None,
            start_chat_callback=self.mock_start_chat_callback,
            output_requested_callback=self.mock_output_requested_callback,
            llm_stream_finished_callback=self.mock_llm_stream_finished_callback
        )

        # Assert Chat events are still bound
        chat_calls = [
            call(event_name="chat_sent", listener=self.mock_start_chat_callback),
            call(event_name="output_requested", listener=self.mock_output_requested_callback)
        ]
        self.mock_chat.add_event.assert_has_calls(chat_calls, any_order=True)

        # Assert LLM event is NOT bound
        self.mock_llm.add_event.assert_not_called()