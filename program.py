import os
import logging
import json # Import the json module

from config import ProgramConfig, ProgramSetting
from core import Chat, ChatCommandInterceptor, CommandExecutor
from core.llms import ModelParams, BaseModel, OllamaModel, HuggingFaceModel, T5Model # Import T5Model
from color import Color, format_text
from extras import ConsoleTokenFormatter
import functions as func


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
        llm (BaseModel): The language model bot (can be OllamaModel, HuggingFaceModel, or T5Model).
        active_executor (CommandExecutor): The active executor.
        token_states (dict): Token states for formatting output.
    """

    # Define the default path for the model configuration JSON
    MODEL_CONFIG_FILE = "model_config.json"

    def __init__(self) -> None:
        """
        Initializes the program with default settings.
        """
        self.config: ProgramConfig = None
        self.model_name: str = "__no_model__"
        self.model_variant = None
        self.system_prompt: str = None
        self.model_chat_name: str = None
        self.chat = Chat()
        self.command_interceptor = None
        self.llm: BaseModel = None # Type hint as BaseModel for flexibility
        self.active_executor: CommandExecutor = None
        self.token_processor = ConsoleTokenFormatter()
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self._logger = logging.Logger(name=__file__)
        self.model_params = ModelParams()
    
    def init_program(self, args=None) -> None:
        """Loads configuration and initializes program components."""
        self.load_config(args=args)
        self.clear_on_init: bool = args.msg is not None or args.debug
        self.init()

    def init_model_params(self):
        """Initializes model parameters."""
        self.model_params.num_ctx = BaseModel.CONTEXT_WINDOW_LARGE

    def init(self) -> None:
        """
        Initializes the program with configuration settings, including model loading.
        """
        
        # Load the system prompt
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        self.system_prompt = self.read_system_file(system_file) 


        # Load the model based on JSON configuration
        self.model_name: str = ProgramConfig.current.get("MODEL_CONFIG_NAME")
        self._load_model(self.model_name)
        
        # Ensure model was loaded successfully before proceeding
        if self.llm is None or self.llm.model is None:
            func.log(f"CRITICAL: Failed to load LLM model. Exiting.")
            sys.exit(1) # Exit if model loading failed

        # Update model_name and variant from the loaded model object if it exists
        self.model_name = self.llm.model_name 
        spliced_model_name = self.model_name.split(":")
        self.model_chat_name: str = spliced_model_name[0]
        self.model_variant = spliced_model_name[1] if len(spliced_model_name) > 1 else None

        self.init_model_params()
        self.command_interceptor = ChatCommandInterceptor(self.chat, self.config.get("PATHS_CHAT_LOG"))
        self.active_executor: CommandExecutor = None
        self.chat = Chat()


    def process_token(self, token):
        """Processes a token for console output."""
        return self.token_processor.process_token(token)

    def clear_process_token(self):
        """Clears the token processor state."""
        self.token_processor.clear_process_token()

    def start_chat(self, user_input):
        """
        Starts a chat session with the language model.

        Args:
            user_input (str): The user's input message.
        """
        started_response = False
        outs = self.llm.chat(
            self.chat.messages,
            images=self.chat.images,
            options=self.model_params.to_dict(),
        )
        for text in outs:
            if not started_response:
                func.out(
                    format_text(self.chat.assistant_prompt, Color.PURPLE) + Color.RESET,
                    end=" ",
                )
                started_response = True

            new_token = self.process_token(text)
            self.chat.current_message += text
            func.out(new_token, end="", flush=True)

    def llm_stream_finished(self, data):
        """
        Handles the finished event for the language model stream.

        Args:
            data (ExecutorResult): The result of the executor.
        """
        func.out("\n")
        self.clear_process_token()
        self.chat.chat_finished()

    def output_requested(self):
        """Requests output from the active executor."""
        if self.active_executor:
            self.active_executor.output_requested()

    def load_events(self):
        """Loads events for the chat and language model."""
        self.chat.add_event(
            event_name=self.chat.EVENT_CHAT_SENT, listener=self.start_chat
        )
        self.chat.add_event(
            event_name=self.chat.EVENT_OUTPUT_REQUESTED, listener=self.output_requested
        )
        self.llm.add_event(
            event_name=self.llm.STREAMING_FINISHED_EVENT,
            listener=self.llm_stream_finished,
        )

    def load_config(self, args=None):
        """
        Loads configuration settings from a file.

        Args:
            args (argparse.Namespace): The command-line arguments.
        """
        self.config = ProgramConfig.load()

        if args is None:
            return

        # Override with arguments
        
        # override with arguments    
        if args.model: ProgramConfig.current.set(key='MODEL_CONFIG_NAME', value=args.model)

        if args.system:
            
            filepath: str = os.path.join(
                self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES), args.system.replace(".md", "") + ".md"
            )
            if os.path.exists(filepath):
                self.config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
           
        if args.system_file:
            filepath = args.system_file
            if os.path.exists(filepath):
                self.config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)

        self.config.set(ProgramSetting.PRINT_LOG, args.no_log)
        self.config.set(ProgramSetting.PRINT_OUTPUT, args.no_out)

    def start_chat_loop(self) -> None:
        """Runs the program's main loop."""
        self.load_events()
        self.chat.loop()

    def read_system_file(self, system_file: str) -> str:
        """Reads the content of a system prompt file."""
        system_templates_dir = self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES, {})
        
        system_filepath = os.path.join(system_templates_dir,system_file.replace(".md","")+".md")

        if os.path.exists(system_file): # Check if the path itself is valid
            return func.read_file(system_file)
        elif os.path.exists(system_filepath): # Check user specific path
            return func.read_file(system_filepath)
        else:
            func.log(f"WARNING: System prompt file '{system_file}' not found at any known location.")
            return ""

    def _load_model(self, model_config_name) -> BaseModel:
        """
        Loads the appropriate LLM model based on `model_config`.
        """
        folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS) or os.path.join( dirname(__file__), "templates") 
        filename = os.path.join(folder, model_config_name)
        model_config = json.loads(func.read_file(filename))
        
        model_name = model_config.get("model_name")
        model_type = model_config.get("model_type")
        model_properties = model_config.get("model_properties", {})

        if not model_name or not model_type:
            func.log("ERROR: 'model_name' or 'model_type' missing in model configuration.")
            sys.exit(1)

        func.log(f"Checking system :")
        func.log(Color.YELLOW + f"  Loading {model_name} (Type: {model_type})")

        # Extract common properties for the constructor
        quantize = model_properties.get("quantize", False)
        # Assuming system_prompt is handled by Program.init()
        
        # Check for specific model types
        if model_type == "causal_lm":
            self.llm = HuggingFaceModel(
                model_name,
                system_prompt=self.system_prompt,
                quantize=quantize
            )
            func.log(f"INFO: Model '{model_name}' loaded as a Causal Language Model.")
        elif model_type == "seq2seq_lm":
            self.llm = T5Model(
                model_name,
                system_prompt=self.system_prompt,
                quantize=quantize
            )
            func.log(f"INFO: Model '{model_name}' loaded as a Seq2Seq Language Model (T5-type).")
        elif model_type == "ollama": # Add support for Ollama based on config
            self.llm = OllamaModel(
                model_name,
                system_prompt=self.system_prompt,
                host=self.config.get(ProgramSetting.OLLAMA_HOST)
            )
            func.log(f"INFO: Model '{model_name}' loaded as an Ollama Model.")
        else:
            func.log(f"ERROR: Unknown model_type '{model_type}' in model configuration.")
            sys.exit(1)

        # Apply general model properties to self.llm.options
        if self.llm and hasattr(self.llm, 'options') and isinstance(self.llm.options, ModelParams):
            for key, value in model_properties.items():
                if hasattr(self.llm.options, key):
                    setattr(self.llm.options, key, value)
                    
        return self.llm # Return the loaded LLM object

