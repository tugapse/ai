# services/event_binder.py

from core.llms import BaseModel
from core.chat import Chat
from typing import Callable

class EventBinder:
    """
    Manages the binding of event listeners for chat and LLM events.
    """

    @staticmethod
    def bind_core_events(chat: Chat, llm: BaseModel, start_chat_callback: Callable, output_requested_callback: Callable, llm_stream_finished_callback: Callable):
        """
        Binds the core application events to their respective listeners.

        Args:
            chat (Chat): The Chat instance.
            llm (BaseModel): The LLM instance.
            start_chat_callback (Callable): The callback function for when a chat message is sent.
            output_requested_callback (Callable): The callback function for when output is requested.
            llm_stream_finished_callback (Callable): The callback function for when the LLM stream finishes.
        """
        chat.add_event(
            event_name=chat.EVENT_CHAT_SENT,
            listener=start_chat_callback
        )
        chat.add_event(
            event_name=chat.EVENT_OUTPUT_REQUESTED,
            listener=output_requested_callback
        )
        if llm: # Ensure LLM exists before trying to add its event
            llm.add_event(
                event_name=BaseModel.STREAMING_FINISHED_EVENT,
                listener=llm_stream_finished_callback,
            )

