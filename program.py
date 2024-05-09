
import json
import os

from dotenv import load_dotenv

from ai.chat import Chat
from ai.chat_command_interceptor import ChatCommandInterceptor
from ai.color import Color
from ai.command_executor import CommandExecutor
from ai.llm import LLMBot
from ai.color import format_text


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
        self.model_variant = None 
        self.system_prompt :str = None
        self.model_chat_name :str = None
        self.chat = Chat()
        self.command_interceptor = None
        self.llm = LLMBot(None, system_prompt=None)
        # self.microphone = Microphone()
        self.active_executor:CommandExecutor = None
        self.token_states = {'printing_block':False}
        self.clear_on_init  = True
        self.write_to_file = False
        self.output_filename = None

    def init(self):
        """
        Initializes the program with configuration settings.
        """
        self.model_name :str = self.config.get("MODEL_NAME")
        self.model_chat_name :str = self.model_name.split(":")[0] 
        self.model_variant = self.model_name.split(":")[1] or None 

        self.system_prompt :str = None
        with  open(self.config.get("SYSTEM_PROMPT_FILE"), 'r') as file:
            self.system_prompt = file.read()    
        
        self.chat  = Chat()
        self.llm = LLMBot( self.model_name, system_prompt=self.system_prompt)
        # self.microphone = Microphone()
        paths = self.config.get('PATHS')
        self.command_interceptor = ChatCommandInterceptor(self.chat, paths['CHAT_LOG'])
        self.active_executor:CommandExecutor = None
        self.token_states = {'printing_block':False}

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
        outs = self.llm.chat(self.chat.messages,options={'num_ctx':LLMBot.CONTEXT_WINDOW_LARGE})
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
        self.clear_process_token()
        self.chat.chat_finished()

    def output_requested(self):
        """
        Requests output from the active executor.
        """
        if self.active_executor: self.active_executor.output_requested()

    def load_events(self):
        """
        Loads events for the chat and language model.
        """
        self.chat.add_event(self.chat.EVENT_CHAT_SENT, self.start_chat)
        self.chat.add_event(self.chat.EVENT_OUTPUT_REQUESTED, self.output_requested)
        self.llm.add_event(self.llm.STREAMING_FINISHED_EVENT,self.llm_stream_finished)

    def load_config(self, args=None):
        """
        Loads configuration settings from a file.
        
        Args:
            args (argparse.Namespace): The command-line arguments.
        """
        load_dotenv()
        root = os.path.dirname(__file__)
        config_filename = os.environ.get('AI_ASSISTANT_CONFIG_FILENAME',os.path.join(root,"config.json"))  
        with  open(config_filename , 'r') as file:
            file_content = file.read().replace("{root_dir}",root)
            self.config = json.loads(file_content)

        if args is None: return
          
         # override with arguments    
        if args.model: self.config['MODEL_NAME'] = args.model

        if args.system: 
            filepath = os.path.join(
                os.path.dirname(__file__), "templates/system", 
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
