import os
import json
from datetime import datetime
from core.events import Events
from color import Color, format_text
import functions as func
from core.llms.base_llm import BaseModel

# Assuming ProgramConfig and ProgramSetting are accessible here if needed for paths
# from config import ProgramConfig, ProgramSetting 


class ChatRoles:
    """
    Define constants for user roles in the chat.

    Attributes:
        USER (str): User role constant.
        ASSISTANCE (str): Assistance role constant.
        SYSTEM (str): System role constant.
        CONTROL (str): Control role constant.
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    CONTROL = "control"


class Chat(Events):
    """
    Define the chat class that handles user input and outputs.
    """

    EVENT_CHAT_SENT = 'chat_sent'
    EVENT_COMMAND_STARTED = 'command_started'
    EVENT_OUTPUT_REQUESTED = 'output_requested'
    EVENT_MESSAGES_UPDATED = 'messages_updated'

    def __init__(self):
        super().__init__()
        self.terminate = False
        self.terminate_tokens = [ 'quit', 'q' ]
        self.running_command = False
        self.waiting_for_response = False
        self.messages = []
        self.images :list[str]= []
        self.current_message = ""
        self.user_prompt = "User:"
        self.assistant_prompt = "Assistant:"
        self.max_chat_log = 50
        self.cache_messages = True
        self.current_prompt = ""
        self._is_multiline_input = False
        self._multiline_input = ""
        self.session_chat_filepath = None 

    def _add_message(self, message_dict: dict):
        """
        Add a new message to the chat log.
        Args:
            message_dict (dict): A dictionary with 'role' and 'content' keys.
        """
        if self.cache_messages:
            self.messages.append(message_dict)
            self._check_messages_size(self.max_chat_log)

    def _reset_chat(self):
        self.messages = []

    def _check_messages_size(self, max_messages):
        if len(self.messages) > max_messages:
            self.messages.pop(0)

    def loop(self):
        while not self.terminate:
            self.process_loop_frame()

    def check_and_handle_user_input_multiline(self, user_input:str):
        if user_input is not None and len(user_input.strip()) > 0:          
            if self._is_multiline_input:
                if user_input.strip().endswith('"""'):
                    self._is_multiline_input = False
                    self._multiline_input += user_input.strip()
                    self.send_chat(self._multiline_input)
                    self._multiline_input = ""
                else:
                    self._multiline_input += user_input+"\n"
                return True
            elif user_input.strip().startswith('"""'):
                self._multiline_input += user_input.strip()
                self._is_multiline_input = True
                return True          
        return False

    def process_loop_frame(self):
        # Only prompt for input if not running a command AND not waiting for an LLM response
        if not self.running_command and not self.waiting_for_response:
            if self._is_multiline_input:
                user_input = input("... ")
            else:
                func.out(format_text(self.user_prompt, Color.BLUE) , flush=True)
                user_input = input()

            if len(user_input.strip()) == 0:
                func.out("\r",end="",flush=True)
                return

            if user_input.startswith('/'):
                self.run_command(user_input)

            elif user_input.lower() in self.terminate_tokens:
                self.terminate_chat()
            
            else:
                if not self.check_and_handle_user_input_multiline(user_input):  
                    self.send_chat(user_input)
        # If running_command or waiting_for_response is True, this frame does nothing,
        # relying on the state to change in an event handler (like llm_stream_finished)
        # for the next frame to then process input.

    def send_chat(self, message_content: str):
        
        self.waiting_for_response = True
        self._add_message(BaseModel.create_message(ChatRoles.USER, message_content))
        self.trigger(self.EVENT_CHAT_SENT, message_content)

    def output_requested(self, message):
        self.trigger(self.EVENT_OUTPUT_REQUESTED, message)

    def start_command(self, message):
        self.trigger(self.EVENT_COMMAND_STARTED, message)

    def run_command(self, message):
        if self.running_command:
            return

        self.running_command = True
        self.start_command(message)

    def terminate_chat(self):
        self.terminate = True
        func.out(format_text( "Chat terminated.", Color.BLUE))

    def terminate_command(self):
        self.running_command = False

    def chat_finished(self):
        from core.llms.base_llm import BaseModel
        self.waiting_for_response = False # This is correctly set to False
        # current_message is intended for console display, so reset it here.
        # The actual response content for history is handled in program.py's finally block.
        # Ensure that whatever `self.current_message` contained before `chat_finished` was
        # already properly stripped of the EOS token in `program.py` before it was assigned.
        self._add_message(BaseModel.create_message(ChatRoles.ASSISTANT, self.current_message.strip()))
        self.current_message = "" # Reset for next assistant message

    def save_chat_history(self, chat_log_folder=None):
        """
        Saves the current chat history to a JSON file.
        This method will now be a placeholder, as the `Program` class will handle the actual file saving.
        It's kept here because `Program` was calling `self.chat.save_chat_history()`.
        """
        pass
