import json
from pathlib import Path
from ai.color import Color
from ai.core import ChatRoles

class ConsoleChatReader:

    def __init__(self, filename) -> None:
        self.filename = filename
        self.path_file = Path(filename)  
        self.content = None   
        self.token_processor = ConsoleTokenFormatter()    

    def load(self): 
        if  not self.path_file.exists():
            raise FileNotFoundError(self.filename)
        j_obj:list = json.loads(self.path_file.read_text())
        for chat_message in j_obj:
            self._print_chat(chat_message)
        

    def _print_chat(self,chat_message):
        #dont process system messages
        if chat_message['role'] == ChatRoles.SYSTEM: return
        color:Color = Color.BLUE if chat_message['role'] == ChatRoles.USER else Color.YELLOW
        text:str = "User :" if chat_message['role'] == ChatRoles.USER else "Assistant"
        
        content:str = chat_message.get("content")
        colored_text = self.color_text(content)         
        print(f"{color}{text} {Color.RESET} {colored_text}",flush=True, end="\n\n")

    def color_text(self, text:str):
        colored_text = ""
        for token in text.split(" "):
            colored_text+=self.token_processor.process_token(token) + " "
        return colored_text

class ConsoleTokenFormatter:
    
    def __init__(self) -> None:
        self.token_states: dict[str, bool] = {
            'printing_block':False
        }
        
    def process_token(self, token):
        """
        Processes a token and formats it for output.
        
        Args:
            token (str): The token to process.
        
        Returns:
            str: The processed token.
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
        self.token_states['printing_block'] = False
 