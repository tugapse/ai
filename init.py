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
        print(format_text(self.chat.assistant_prompt, Color.PURPLE)+Color.RESET, end= " ")
        for text in outs:
            new_token = self.process_token(text)
            self.chat.current_message += text
            print(new_token, end="", flush=True)

    def llm_stream_finished(self,data):
        print("\n")
        self.chat.chat_finished()
        # message =self.chat.messages[-1]
        # text = message['content']
        # if command := self.tool_inspector.check_tool_request(text): 
        #     self.chat.hide_loading()
        #     print(command)

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
    parser.add_argument('--folderfiles', type=str, help='Load multiple files from folder and pass them as a message with file location and file content')
    parser.add_argument('--extension', type=str, help='Provides File extension for folder files search')
    parser.add_argument('--task', type=str, help='name of the template inside prompt_templates/task, do not insert .md')
    parser.add_argument('--task-file', type=str, help='name of the template inside prompt_templates/task, do not insert .md')

    return parser.parse_args()

def print_initial_info(prog:Program, args):

    func.clear_console()
    func.set_console_title("Ai assistant: " + prog.model_chat_name)
    system_p_file = prog.config['SYSTEM_PROMPT_FILE'].split("/")[-1]
    print(Color.GREEN,end="")
    print(f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant")
    print(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file")
    print(f"{Color.RESET}--------------------------")
    
        
def ask(llm:LLMBot, text:[str, list[str]], args=None):

    if isinstance(text, str):
        message = [llm.create_message(ChatRoles.USER,text)]
        print("Prompt has " + str(len(text)/4) + " tokens in a " + str(len(text)) + "chars string")
    elif isinstance(text, int):
        message = [llm.create_message(ChatRoles.USER, str(text))]
        print("Prompt has " + str(len(text) / 4) + " tokens in a " + str(len(text)) + "chars string")
    elif isinstance(text, list):
        message = text
        txt_len = 0

        for line in text:
            txt_len = txt_len + len(line['content'])
        print("Prompt has " + str(txt_len / 4) + " tokens in a " +str(txt_len) + "chars string")
    else:
        print("Unsupported text type")

    print("Loading ֍ ֍ ֍\n")

    for response in llm.chat(message ):
        print(response, end="",flush=True)
    print("\nK, thanks, bey!")

def read_file(filename)->str:
    if not os.path.exists(filename):
        pformat_text("File not found > " + filename,Color.RED)
        exit(1)
    return Path(filename).read_text()

# def read_folder_files(folder_path)->str:
#     output = list()
#
#     if not os.path.exists(folder_path):
#         pformat_text("Folder not found > " + folder_path,Color.RED)
#         exit(1)
#     else:
#         output.append("#FOLDER LIST FILES OUTPUT ================================================")
#         for root, subdirs, files in os.walk(folder_path):
#             for file in files:
#                 if ".php" in file:
#                     output.append("#" + root + "\\" + file)
#                     output.append(Path(root + "\\" + file).read_text())
#
#     return '\n'.join( str(line) for line in output)
def read_folder_files(folder_path)->str:
    output = list()

    if not os.path.exists(folder_path):
        pformat_text("Folder not found > " + folder_path,Color.RED)
        exit(1)
    elif not args.extension:
        pformat_text("Additional argument required for folderfiles: extension", Color.RED)
        pformat_text("→ Missing file extension to look for in folder (eg: --extension='txt')", Color.YELLOW)
        exit(1)
    else:
        for root, subdirs, files in os.walk(folder_path):
            for file in files:
                if "."+args.extension in file:
                    filename = os.path.join(root,file)
                    output.append( { 'filename': filename,'content': Path(filename).read_text() } )

    output.append({'filename': "is-prompt", 'content': "\n"+args.msg})
    return output

if __name__ == "__main__":
    prog = Program()
    args = load_args()

    if args.list_models: 
        os.system("ollama list")
        exit(0)
        
    prog.load_config(args)
    prog.clear_on_init = args.msg is not None
    prog.init()

    if args.task:
        filename = os.path.join(prog.config['PATHS']['TASK_USER_PROMPT'],args.task.replace(".md","")+".md")
        task = read_file(filename)
        args.msg = task

    if args.task_file:
        task = read_file(args.task_file)
        args.msg = task

    text_file=""
    if args.file:
        text_file = read_file(args.file)
        prog.chat._add_message(ChatRoles.USER, f"File: {args.file} \n\n  ```{text_file}```")

    # if args.folderfiles:
    #     php_files = read_folder_files(args.folderfiles)
    #     #print(text_file)
    #     prog.chat._add_message(ChatRoles.USER, f"```{php_files}```")
    #     #exit(0)

    if args.folderfiles:
        php_files = read_folder_files(args.folderfiles)
        messages = list()

        #messages.append(prog.llm.create_message(ChatRoles.USER, 'Do the following task in all the files described, ' + args.msg+ '\n'))

        for file in php_files:
            messages.append(prog.llm.create_message(ChatRoles.USER, 'File Path: ' + file['filename'] + '\n File Content:\n' + file['content']+ '\n'))

        #messages.append(prog.llm.create_message(ChatRoles.USER,  args.msg+ ', do the following task in ALL the File Content given'))

        #print('\n'.join(str(line) for line in messages))
        #exit(0)

        ask(prog.llm, messages)
        exit(0)

    if args.msg:
        if args.file:
            args.msg =  f"File: {args.file} \n\n  ```{text_file}``` \n\n {args.msg} "
        ask(prog.llm, args.msg)
        exit(0)
        
    print_initial_info(prog,args)
    prog.main()   