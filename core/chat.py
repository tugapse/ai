from core.events import Events
from color import Color, format_text
import functions as func


class ChatRoles:
    """
    Define constants for user roles in the chat.

    Attributes:
        USER (str): User role constant.
        ASSISTANCE (str): Assistance role constant.
        SYSTEM (str): System role constant.
    """

    # Constants for user roles
    USER = "user"
    ASSISTANCE = "assistance"
    SYSTEM = "system"
    CONTROL = "control"


class Chat(Events):
    """
    Define the chat class that handles user input and outputs.

    Attributes:
        EVENT_CHAT_SENT (str): Event type for sent chat messages.
        EVENT_COMMAND_STARTED (str): Event type for started commands.
        EVENT_OUTPUT_REQUESTED (str): Event type for requested output.
        EVENT_MESSAGES_UPDATED (str): Event type for updated messages.

    Methods:
        __init__(): Initialize the chat instance.
        _add_message(role, message): Add a new message to the chat log.
        _reset_chat(): Reset the chat log.
        _check_messages_size(max_messages): Check and trim the chat log size.
        loop(): Run the chat loop until terminated.
        check_and_handle_user_input_multiline(user_input): Handle multiline user input.
        process_loop_frame(): Process a frame in the chat loop.
        send_chat(message): Send a new chat message.
        output_requested(message): Request output for a given message.
        start_command(message): Start a command with the given message.
        run_command(message): Run a command with the given message.
        terminate_chat(): Terminate the chat.
        terminate_command(): Terminate an ongoing command.
        chat_finished(): Mark the end of a chat session.

    """

    # Event types
    EVENT_CHAT_SENT = 'chat_sent'
    EVENT_COMMAND_STARTED = 'command_started'
    EVENT_OUTPUT_REQUESTED = 'output_requested'
    EVENT_MESSAGES_UPDATED =  'messages_updated'

    def __init__(self):
        """
        Initialize the chat instance.

        Attributes:
            terminate (bool): Flag to indicate whether the chat should be terminated.
            terminate_tokens (list[str]): List of tokens that can terminate the chat.
            running_command (bool): Flag to indicate whether a command is currently running.
            waiting_for_response (bool): Flag to indicate whether the chat is waiting for a response.
            messages (list[dict]): The chat log, stored as a list of dictionaries with 'role' and 'content' keys.
            current_message (str): The current message being processed.
            user_prompt (str): The prompt string for user input.
            assistant_prompt (str): The prompt string for assistant output.
            max_chat_log (int): The maximum size of the chat log.
            cache_messages (bool): Flag to indicate whether messages should be cached in memory.
            current_prompt (str): The current prompt string.
             _is_multiline_input (bool): Flag to indicate whether the input is multiline.
             _multiline_input (str): The multiline input buffer.

        """
        super().__init__()
        self.terminate = False
        # List of tokens that can terminate the chat
        self.terminate_tokens = [ 'quit', 'q' ]
        self.running_command = False
        self.waiting_for_response = False
        self.messages = []
        self.images :list[str]= []
        self.current_message = ""
        self.user_prompt = "  User:"
        self.assistant_prompt = "  Assistant:"
        self.max_chat_log = 50  # Maximum size of the chat log
        self.cache_messages = True
        self.current_prompt = ""
        self._is_multiline_input = False
        self._multiline_input = ""

    def _add_message(self, role, message):
        """
        Add a new message to the chat log.

        Args:
            role (str): The role of the message sender.
            message (str): The content of the message.

        Attributes:
            messages (list[dict]): The chat log, stored as a list of dictionaries with 'role' and 'content' keys.

        """
        if self.cache_messages:
            # Add new message to the chat log
            self.messages.append({'role': role, 'content': message})
            self._check_messages_size(self.max_chat_log)

    def _reset_chat(self):
        """
        Reset the chat log.
        
        Attributes:
            messages (list[dict]): The chat log, stored as a list of dictionaries with 'role' and 'content' keys.

        """
        # Reset the chat log
        self.messages = []

    def _check_messages_size(self, max_messages):
        """
        Check and trim the chat log size if it exceeds the maximum allowed size.
        
        Args:
            max_messages (int): The maximum allowed size of the chat log.

        Attributes:
            messages (list[dict]): The chat log, stored as a list of dictionaries with 'role' and 'content' keys.

        """
        # Check if the message count is greater than the maximum allowed
        if len(self.messages) > max_messages:
            self.messages.pop(0)

    def loop(self):
        """
        Run the chat loop until terminated.
        
        Attributes:
            terminate (bool): Flag to indicate whether the chat should be terminated.

        """
        while not self.terminate:
            # Process a frame in the chat loop
            self.process_loop_frame()

    def check_and_handle_user_input_multiline(self, user_input:str):
        """
        Handle multiline user input.
        
        Args:
            user_input (str): The user input to process.

        Returns:
            bool: True if the input is multiline, False otherwise.

        Attributes:
             _is_multiline_input (bool): Flag to indicate whether the input is multiline.
             _multiline_input (str): The multiline input buffer.

        """
        if user_input is not None and len(user_input.strip()) > 0:          

            if self._is_multiline_input:
                if  user_input.strip().endswith('"""'):
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
        """
        Process a frame in the chat loop.
        
        Attributes:
            running_command (bool): Flag to indicate whether a command is currently running.
            waiting_for_response (bool): Flag to indicate whether the chat is waiting for a response.

        """
        if self.running_command:
            # Check user input and handle it
            user_input = input()
            self.output_requested(user_input)
            return  # Skip the rest of the loop and go to next iteration
        elif self.waiting_for_response:
            return
        
        elif self._is_multiline_input:
            user_input = input("... ")
        else:
            func.out(format_text(self.user_prompt, Color.BLUE) , end=" ",flush=True)
            user_input = input()

        if len(user_input.strip()) == 0:
            func.out("\r",end="",flush=True)
            return

        # Check for command start
        if user_input.startswith('/'):
            self.run_command(user_input)

        elif user_input.lower() in self.terminate_tokens:
            self.terminate_chat()
        
        else:
            if not self.check_and_handle_user_input_multiline(user_input): 
                self.send_chat(user_input)    

    def send_chat(self, message):
        """
        Send a new chat message.

        Args:
            message (str): The content of the message to be sent.

        Attributes:
            waiting_for_response (bool): Flag to indicate whether the chat is waiting for a response.
             _add_message(role, message): Add a new message to the chat log.

        """
        self.waiting_for_response = True
        # Send the message and trigger event
        self._add_message(ChatRoles.USER, message)
        self.trigger(self.EVENT_CHAT_SENT, message)

    def output_requested(self, message):
        """
        Request output for a given message.
        
        Args:
            message (str): The content of the message to be used for requesting output.

        Attributes:
            trigger(event_type, message): Trigger an event with the given message.

        """
        # Send the request and trigger event
        self.trigger(self.EVENT_OUTPUT_REQUESTED, message)

    def start_command(self, message):
        """
        Start a command with the given message.
        
        Args:
            message (str): The content of the message to be used for starting the command.

        Attributes:
            trigger(event_type, message): Trigger an event with the given message.

        """
        # Send the request and trigger event
        self.trigger(self.EVENT_COMMAND_STARTED, message)

    def run_command(self, message):
        """
        Run a command with the given message.
        
        Args:
            message (str): The content of the message to be used for running the command.

        Attributes:
            running_command (bool): Flag to indicate whether a command is currently running.

        """
        if self.running_command:     # Check if the command has already started
            return  # Exit early if the command has already started

        self.running_command = True  # Set the running command flag to True
        self.start_command(message)

    def terminate_chat(self):
        """
        Terminate the chat.
        
        Attributes:
            terminate (bool): Flag to indicate whether the chat should be terminated.

        """
        self.terminate = True
        func.out(format_text( "Chat terminated.", Color.BLUE))


    def terminate_command(self):
        """
        Terminate an ongoing command.
        
        Attributes:
            running_command (bool): Flag to indicate whether a command is currently running.

        """
        self.running_command = False

    def chat_finished(self):
        """
        Mark the end of a chat session.
        
        Attributes:
            waiting_for_response (bool): Flag to indicate whether the chat is waiting for a response.
            _add_message(role, message): Add a new message to the chat log.

        """
        self.waiting_for_response = False
        self._add_message('assistant', self.current_message)
        self.current_message = ""