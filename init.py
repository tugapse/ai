import glob
import os
import json
from itertools import count
import readline
import argparse
from dotenv import load_dotenv
from chat import Chat, ChatRoles
from chat_command_interceptor import ChatCommandInterceptor
from command_executor import CommandExecutor
from llm import LLMBot
from listen import Microphone, ExecutorResult
from color import Color, format_text, pformat_text
import functions as func
from pathlib import Path
import cli_args

class Program:
    """
    Main program class for the AI assistant.
    
    Attributes:
        config (dict): Configuration settings.
        model_name (str): The name of the model to use.
        system_prompt (str): The system prompt file.
        model_chat_name (str): The chat name for the model.
        chat (Chat): The chat object.
        command_interceptor (ChatCommandInterceptor): The command interceptor.
        llm (LLMBot): The language model bot.
        microphone (Microphone): The microphone object.
        active_executor (CommandExecutor): The active executor.
        token_states (dict): Token states for formatting output.
    """

    def __init__(self) -> None:
        """
        Initializes the program with default settings.
        """
        self.config = None
        self.model_name :str = None
        self.system_prompt :str = None
        self.model_chat_name :str = None
        self.chat = Chat()
        self.command_interceptor = None
        self.llm = LLMBot(None, system_prompt=None)
        self.microphone = Microphone()
        self.active_executor:CommandExecutor = None
        self.token_states = {'printing_block':False}
        self.clear_on_init  = True
        self.write_to_file = False
        self.output_filename = None

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

    def start_chat(self, user_input):
        """
        Starts a chat session with the language model.
        
        Args:
            user_input (str): The user's input message.
        """
        started_response = False
        print(Color.YELLOW+"  Loading ..\r", end="")
        outs = self.llm.chat(self.chat.messages,options={'num_ctx':4096})
        for text in outs:
            if not started_response:
                print(format_text(self.chat.assistant_prompt, Color.PURPLE)+Color.RESET, end= " ")
                started_response = True
                
            new_token = self.process_token(text)
            self.chat.current_message += text
            print(new_token, end="", flush=True)

    def llm_stream_finished(self, data):
        """
        Handles the finished event for the language model stream.
        
        Args:
            data (ExecutorResult): The result of the executor.
        """
        print("\n")
        self.chat.chat_finished()
        self.clear_process_token()

    def output_requested(self):
        """
        Requests output from the active executor.
        """
        if self.active_executor: self.active_executor.output_requested()

    def init(self):
        """
        Initializes the program with configuration settings.
        """
        self.model_name :str = self.config["MODEL_NAME"]
        self.model_chat_name :str = self.model_name.split(":")[0] 

        self.system_prompt :str = None
        with  open(self.config["SYSTEM_PROMPT_FILE"], 'r') as file:
            self.system_prompt = file.read()    
        
        self.chat  = Chat()
        self.llm = LLMBot( self.model_name, system_prompt=self.system_prompt)
        self.microphone = Microphone()
        self.command_interceptor = ChatCommandInterceptor(self.chat, self.config['PATHS']['CHAT_LOG'])
        self.active_executor:CommandExecutor = None
        self.token_states = {'printing_block':False}

    def load_events(self):
        """
        Loads events for the chat and language model.
        """
        self.chat.add_event(self.chat.EVENT_CHAT_SENT, self.start_chat)
        self.chat.add_event(self.chat.EVENT_OUTPUT_REQUESTED, self.output_requested)
        self.llm.add_event(self.llm.STREAMING_FINISHED_EVENT,self.llm_stream_finished)

    def load_config(self, args):
        """
        Loads configuration settings from a file.
        
        Args:
            args (argparse.Namespace): The command-line arguments.
        """
        load_dotenv()
        root = os.path.dirname(__file__)
        with  open(os.path.join(root,"config.json"), 'r') as file:
            file_content = file.read().replace("{root_dir}",root)
            self.config = json.loads(file_content)
            
         # override with arguments    
        if args.model: self.config['MODEL_NAME'] = args.model

        if args.system: 
            filepath = os.path.join(
                os.path.dirname(__file__), "templates", 
                args.system.replace(".md","")+".md")            
            if os.path.exists(filepath): self.config['SYSTEM_PROMPT_FILE'] = filepath 

        if args.system_file: 
            filepath = args.system_file.replace(".md","")+".md"
            if os.path.exists(filepath): self.config['SYSTEM_PROMPT_FILE'] = filepath 
            
    def main(self):
        """
        Runs the program's main loop.
        """
        self.load_events()
        self.chat.loop()

def load_args():
    """
    Loads command-line arguments for the program.
    
    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
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
    """
    Prints initial information about the program.
    
    Args:
        prog (Program): The program object.
        args (argparse.Namespace): The command-line arguments.
    """
    func.clear_console()
    func.set_console_title("Ai assistant: " + prog.model_chat_name)
    system_p_file = prog.config['SYSTEM_PROMPT_FILE'].split("/")[-1]
    print(Color.GREEN,end="")
    print(f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant")
    print(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file")
    print(f"{Color.RESET}--------------------------")

def ask(llm:LLMBot, input_message:[str, list[str]], args=None):
    """
    Asks the language model a question.
    
    Args:
        llm (LLMBot): The language model bot.
        input_message ([str, list[str]]): The user's input message.
        args (argparse.Namespace): The command-line arguments.
    """
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
    llm_options = {
            'num_ctx': 16384,
            'temperature':0.0
    }
    for response in llm.chat(message, True,options=llm_options):
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