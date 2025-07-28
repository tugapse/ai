import json
import os
from core.chat import Chat
from color import Color
from extras import ConsoleChatReader
import functions as func


class ChatCommandInterceptor:
    """
    This class is responsible for intercepting and handling commands in a chat session.
    
    Attributes:
        - chat (Chat): The chat object that this interceptor is attached to.
        - root_folder (str): The root folder where chat sessions are stored.
        - extra_commands (list): A list of custom commands that this interceptor handles.
    """

    def __init__(self, chat: Chat, root_folder: str) -> None:
        """
        Initializes the ChatCommandInterceptor with a chat object and a root folder.

        Args:
            - chat (Chat): The chat object to attach this interceptor to.
            - root_folder (str): The root folder where chat sessions are stored.
        """
        self.chat = chat
        self.root_folder = root_folder
        self.chat.add_event(Chat.EVENT_COMMAND_STARTED, self.run)
        self.extra_commands = []

    def run(self, command_text: str) -> None:
        """
        Handles a command by splitting it into parts and determining what action to take.

        Args:
            - command_text (str): The text of the command to handle.
        """
        parts = command_text.split()
        command = parts[0]

        if command in ['/save', '/load', '/list']:
            # Handle save, load, or list commands
            if command_text.startswith('/save'):
                self.save_session(parts[1])
            elif command_text.startswith('/load'):
                self.load_session(parts[1])
            elif command_text.startswith('/list'):
                self.list_sessions()
        elif command in self.extra_commands:
            # Handle custom commands
            if self.handled_extra_command(command_text):
                return
        else:
            func.out("Invalid Command")

        self.chat.terminate_command()

    def save_session(self, filename: str) -> None:
        """
        Saves the current chat session to a file.

        Args:
            - filename (str): The name of the file to save the session to.
        """
        os.makedirs(self.root_folder, exist_ok=True)

        with open(os.path.join(self.root_folder, filename), 'w') as f:
            json.dump(self.chat.messages, f)
            func.out("=== Session saved ===",level="INFO")

    def load_session(self, filename: str) -> None:
        """
        Loads a chat session from a file.

        Args:
            - filename (str): The name of the file to load the session from.
        """

        if not os.path.exists(os.path.join(self.root_folder, filename)):
            func.out("=== Session not found ===",level="WARNING")
            return
        with open(os.path.join(self.root_folder, filename), 'r') as f:
            self.chat.messages = json.load(f)
            reader = ConsoleChatReader(filename)
            for message in self.chat.messages:
                reader._print_chat(message)
            func.out("=== Session loaded ===",level="WARNING")

    def list_sessions(self) -> None:
        """
        Lists all chat sessions stored in the root folder.
        """
        files_list = [file for file in os.listdir(self.root_folder) if os.path.isfile(os.path.join(self.root_folder, file))]
        func.out("Chat sessions : ")
        for file in files_list:
            func.out(Color.PURPLE + " - " + file + Color.RESET)