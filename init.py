import os
import json
import readline
import argparse
from dotenv import load_dotenv

from chat import Chat, ChatRoles
from tools import ToolSelector, all_tools_info
from command_executor import CommandExecutor
from llm import LLMBot
from listen import Microphone,ExecutorResult
from color import Color, format_text, pformat_text
import functions as func

class Program:
    def __init__(self,) -> None: 
        self.config = None       
        self.model_name :str
        self.system_prompt :str = None
        self.model_chat_name :str = None
        self.chat : Chat = None
        self.llm : LLMBot = None
        self.microphone : Microphone= None
        self.tool_inspector : ToolSelector = None
        self.active_executor:CommandExecutor = None
        self.token_states = {
            'printing_block':False
        }
        self.clear_on_init  = True

    def process_token(self,token):
        result = token
        if '``' in token:
            if self.token_states.get('printing_block') == False:
                result = token + Color.YELLOW
                self.token_states['printing_block'] = True
            else:
                result = token + Color.RESET
                self.token_states['printing_block'] = False
        return result

    def start_chat(self,user_input):
        pformat_text("  Loading ..\r", Color.YELLOW, end="")
        outs = self.llm.chat(self.chat.messages)
        print(format_text(self.chat.assistant_prompt, Color.PURPLE)+Color.RESET, end= "")
        for text in outs:
            new_token = self.process_token(text)
            self.chat.current_message += new_token
            print(text, end="", flush=True)
        print(Color.RESET, end="")

    def chat_finished(self,data):
        print("\n")
        self.chat.chat_finished()
        # message =self.chat.messages[-1]
        # text = message['content']
        # if command := self.tool_inspector.check_tool_request(text): 
        #     self.chat.hide_loading()
        #     print(command)

    def record_finished(self,result:ExecutorResult):
        self.microphone.save_as_wave("./test.wav")
        self.chat.terminate_command()

    def check_command(self,user_input:str):
        if user_input.startswith("/listen"):
            self.active_executor = self.microphone
            self.microphone.start_recording(self.record_finished )
        else:
            format_text("> > Invalid comand < < ",Color.RED)
            self.chat.terminate_command()

    def output_requested(self,):
        if self.active_executor : self.active_executor.output_requested()

    def init(self): 

        self.model_name :str = self.config["MODEL_NAME"]
        self.model_chat_name :str = self.model_name.split(":")[0]
     

        self.system_prompt :str = None
        with  open(self.config["SYSTEM_PROMPT_FILE"], 'r') as file:
            self.system_prompt = file.read()
    
        self.chat  = Chat()
        self.llm = LLMBot( self.model_name, system_prompt=self.system_prompt)
        self.microphone = Microphone()
        self.tool_inspector = ToolSelector(self.model_name)

        self.active_executor:CommandExecutor = None
        self.token_states = {
            'printing_block':False
        }

    def load_events(self):
        self.chat.add_event(self.chat.EVENT_CHAT_SENT, self.start_chat)
        self.chat.add_event(self.chat.EVENT_COMMAND_STARTED, self.check_command)
        self.chat.add_event(self.chat.EVENT_OUTPUT_REQUESTED, self.output_requested)
        self.llm.add_event(self.llm.STREAMING_FINISHED_EVENT,self.chat_finished)
        
    def load_config(self):
        load_dotenv()
        with  open("./config.json", 'r') as file:
            self.config = json.loads(file.read())
        

    def main(self):
        self.load_events()
        self.chat.loop()


        
def load_args():
    parser = argparse.ArgumentParser(description='AI Assistant')
    parser.add_argument('--msg', type=str, help='Direct question')

    return parser.parse_args()

        
def ask(llm:LLMBot,text:str):
    message = llm.create_message(ChatRoles.USER,text)
    print("Loading ..")
    for response in llm.chat([message]):
        print(response, end="",flush=True)
    print("  =======  ")
    
if __name__ == "__main__":
    prog = Program()
    args = load_args()
    prog.load_config()
    prog.clear_on_init = args.msg is not None
    prog.init()
    
    if args.msg:
        ask(prog.llm, args.msg)
        exit(0)
        
    func.clear_console()
    pformat_text(f"Starting { prog.model_chat_name } assistant...",Color.PURPLE)
    func.set_console_title("Ai assistant: " + prog.model_chat_name)
    prog.main()   