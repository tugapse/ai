import glob
import os
import json
from itertools import count

import readline
import argparse
from dotenv import load_dotenv

from chat import Chat, ChatRoles
from command_interceptor import ChatCommandInterceptor
from tools import ToolSelector, all_tools_info
from command_executor import CommandExecutor
from llm import LLMBot
from listen import Microphone,ExecutorResult
from color import Color, format_text, pformat_text
import functions as func

from pathlib import Path
import cli_args


class Program:
    def __init__(self,) -> None: 
        self.config = None       
        self.model_name :str
        self.system_prompt :str = None
        self.model_chat_name :str = None
        self.chat : Chat = None
        self.command_interceptor = None
        self.llm : LLMBot = None
        self.microphone : Microphone= None
        self.tool_inspector : ToolSelector = None
        self.active_executor:CommandExecutor = None
        self.token_states = {
            'printing_block':False
        }
        self.clear_on_init  = True
        self.write_to_file = False
        self.output_filename = None

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
        started_response = False
        print(Color.YELLOW+"  Loading ..\r", end="")
        outs = self.llm.chat(self.chat.messages)
        for text in outs:
            if not started_response:
                print(format_text(self.chat.assistant_prompt, Color.PURPLE)+Color.RESET, end= " ")
                started_response = True
                
            new_token = self.process_token(text)
            self.chat.current_message += text
            print(new_token, end="", flush=True)

    def llm_stream_finished(self,data):
        print("\n")
        self.chat.chat_finished()

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
        self.command_interceptor = ChatCommandInterceptor(self.chat, self.config['PATHS']['CHAT_LOG'])
        self.active_executor:CommandExecutor = None
        self.token_states = {
            'printing_block':False
        }

    def load_events(self):
        self.chat.add_event(self.chat.EVENT_CHAT_SENT, self.start_chat)
        self.chat.add_event(self.chat.EVENT_OUTPUT_REQUESTED, self.output_requested)
        self.llm.add_event(self.llm.STREAMING_FINISHED_EVENT,self.llm_stream_finished)
        
    def load_config(self,args):
        load_dotenv()
        with  open("./config.json", 'r') as file:
            self.config = json.loads(file.read())
            
        # override with arguments    
        if args.model: self.config['MODEL_NAME'] = args.model

        if args.system: 
            filepath = os.path.join(
                os.path.dirname(__file__), "prompt_templates", 
                args.system.replace(".md","")+".md")
            
            if os.path.exists(filepath): self.config['SYSTEM_PROMPT_FILE'] = filepath 

        if args.system_file: 
            filepath = args.system_file.replace(".md","")+".md"
            if os.path.exists(filepath): self.config['SYSTEM_PROMPT_FILE'] = filepath 
            
    def main(self):
        self.load_events()
        self.chat.loop()

    
def load_args():
    parser = argparse.ArgumentParser(description='AI Assistant')
    parser.add_argument('--msg', type=str, help='Direct question')
    parser.add_argument('--model', type=str, help='Model to use')
    parser.add_argument('--system', type=str, help='pass a prompt name ')
    parser.add_argument('--system-file', type=str, help='pass a prompt filename')
    parser.add_argument('--list-models', action="store_true", help='See a list of models available')
    parser.add_argument('--file', type=str, help='Load a file and pass it as a message')
    parser.add_argument('--load-folder', type=str, help='Load multiple files from folder and pass them as a message with file location and file content')
    parser.add_argument('--extension', type=str, help='Provides File extension for folder files search')
    parser.add_argument('--task', type=str, help='name of the template inside prompt_templates/task, do not insert .md')
    parser.add_argument('--task-file', type=str, help='name of the template inside prompt_templates/task, do not insert .md')
    parser.add_argument('--output-file', type=str, help='filename where the output of automatic actions will be saved')

    return parser.parse_args()

def print_initial_info(prog:Program, args):
    func.clear_console()
    func.set_console_title("Ai assistant: " + prog.model_chat_name)
    system_p_file = prog.config['SYSTEM_PROMPT_FILE'].split("/")[-1]
    print(Color.GREEN,end="")
    print(f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant")
    print(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file")
    print(f"{Color.RESET}--------------------------")
    
def ask(llm:LLMBot, input_message:[str, list[str]], args=None):

    if isinstance(input_message, str):
        message = [llm.create_message(ChatRoles.USER,input_message)]
        print("Prompt has " + str(len(input_message)/4) + " tokens in a " + str(len(input_message)) + "chars string")
    elif isinstance(input_message, list):
        message = input_message
        txt_len = 0
        for line in input_message:
            txt_len = txt_len + len(line['content'] or "")
        print("Prompt has " + str(txt_len / 4) + " tokens in a " +str(txt_len) + "chars string")
    else:
        print("Unsupported text type")

    print("Loading ֍ ֍ ֍")

    # ensure to clean the file
    if prog.write_to_file: func.write_to_file(prog.output_filename,"")
    
    for response in llm.chat(message, True):
        new_token = prog.process_token(response)
        print(new_token, end="",flush=True)
        if prog.write_to_file:
            func.write_to_file(prog.output_filename,response,func.FILE_MODE_APPEND)
    print("")

if __name__ == "__main__":
    prog = Program()
    args = load_args()
    prog.load_config(args)
    prog.clear_on_init = args.msg is not None
    prog.init()

    cli_args_processor = cli_args.CliArgs(prog, ask=ask)
    cli_args_processor.parse_args(prog=prog, args=args)

    print_initial_info(prog,args)
    prog.main()   