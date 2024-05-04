import json
import os
from chat import Chat
from color import Color, pformat_text

class ChatCommandInterceptor:
    def __init__(self, chat:Chat, root_folder:str) -> None:
        self.chat = chat
        self.root_folder = root_folder
        self.chat.add_event(Chat.EVENT_COMMAND_STARTED, self.run)
        self.extra_commands = []

    def run(self,command_text:str) -> None:
        parts  = command_text.split()
        command = parts[0]
        
        if command in ["/save","/load","/list"] :

            if command_text.startswith("/save"):
                self.save_session(parts[1])
            elif command_text.startswith("/load"):
                self.load_session(parts[1])
            elif command_text.startswith("/list"):
                self.list_sessions()
                
        elif command in self.extra_commands:
            if self.handled_extra_command(command_text):
                return 
        else:
            pformat_text("Invalid Command")

        self.chat.terminate_command()
    
    def save_session(self, filename):
        os.makedirs(self.root_folder, exist_ok=True)

        with open(os.path.join(self.root_folder,filename), 'w') as f:
            json.dump(self.chat.messages, f)
            pformat_text("! Session saved !",color=Color.BLUE)    

    def load_session(self,filename):
        os.makedirs(self.root_folder, exist_ok=True)
        
        if not os.path.exists(os.path.join(self.root_folder,filename)):
            pformat_text("! Session not found !",color=Color.YELLOW)
            return
        with open(os.path.join(self.root_folder,filename), 'r') as f:
            self.chat.messages = json.load(f)
            pformat_text("! Session loaded !",color=Color.BLUE)    

    def list_sessions(self):
        files_list = [file for file in os.listdir(self.root_folder) if os.path.isfile(os.path.join(self.root_folder, file))]
        print("Chat sessions : ")
        for file in files_list:
            print(Color.PURPLE + "____ " + file + Color.RESET)
        
