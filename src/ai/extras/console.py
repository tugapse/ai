import json
from pathlib import Path
from ai.chat.chat import ChatRoles
from ai.color import Color

import ai.functions as func

class ConsoleChatReader:
    """
    Reads and displays chat history from a specified JSON file to the console.

    This class handles loading structured chat data, iterating through messages,
    and formatting them with appropriate colors based on the speaker (User or Assistant).
    """

    def __init__(self, filename) -> None:
        """
        Initializes the ConsoleChatReader.

        Args:
            filename (str): The path to the JSON file containing the chat history.
        """
        self.filename = filename
        self.path_file = Path(filename)  
        self.content = None   
        self.token_processor = ConsoleTokenFormatter()    

    def load(self): 
        """
        Loads the chat history from the configured JSON file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
        if  not self.path_file.exists():
            raise FileNotFoundError(self.filename)
        j_obj:list = json.loads(self.path_file.read_text())
        for chat_message in j_obj:
            self._print_chat(chat_message)
        

    def _print_chat(self,chat_message):
        """
        Prints a single chat message to the console with appropriate formatting.

        System messages are skipped during printing. User messages are colored blue,
        and Assistant messages are colored yellow.

        Args:
            chat_message (dict): A dictionary representing a single chat message,
                                 expected to contain 'role' and 'content'.
        """
        #dont process system messages
        if chat_message['role'] == ChatRoles.SYSTEM: return
        color:str = Color.BLUE if chat_message['role'] == ChatRoles.USER else Color.YELLOW
        text:str = "User :" if chat_message['role'] == ChatRoles.USER else "Assistant"
        
        content:str = chat_message.get("content")
        colored_text = self.color_text(content)         
        func.out(f"{color}{text} {Color.RESET} {colored_text}",flush=True, end="\n\n")

    def color_text(self, text:str):
        """
        Processes the raw text content by tokenizing it and applying formatting
        based on special characters (like backticks) using the TokenFormatter.

        Args:
            text (str): The raw string content of the message.

        Returns:
            str: The text with formatting applied via token processing.
        """
        colored_text = ""
        for token in text.split(" "):
            colored_text+=self.token_processor.process_token(token) + " "
        return colored_text

class ConsoleTokenFormatter:
    """
    Manages the state and processing of individual tokens to apply specific
    formatting rules, such as highlighting code blocks delimited by backticks.
    """
    
    def __init__(self) -> None:
        """
        Initializes the formatter with an empty state tracking dictionary.
        """
        self.token_states: dict[str, bool] = {
            'printing_block':False
        }
        
    def process_token(self, token):
        """
        Processes a token and formats it for output based on the current state.

        If the token contains '``', it toggles the 'printing_block' state
        and applies color changes accordingly.

        Args:
            token (str): The token to process.

        Returns:
            str: The processed token, potentially wrapped in color codes.
        """
        result = token
        if '``' in token:
            if self.token_states.get('printing_block') == False:
                result = token + Color.YELLOW
                self.token_states['printing_block'] = True
            else:
                result = token + Color.RESET
                self.token_states['printing_block'] = False
        return result

    def clear_process_token(self):
        """
        Resets the internal state of the token processor, typically used
        after a block of text has been fully processed.
        """
        self.token_states['printing_block'] = False
