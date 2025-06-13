import os, logging

from config import ProgramConfig, ProgramSetting
from core import Chat, ChatCommandInterceptor, CommandExecutor
from core.llms import ModelParams, BaseModel, OllamaModel, HuggingFaceModel
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
        llm (OllamaModel): The language model bot.
        active_executor (CommandExecutor): The active executor.
        token_states (dict): Token states for formatting output.
    """

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
        self.llm = None
        self.active_executor: CommandExecutor = None
        self.token_processor = ConsoleTokenFormatter()
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self._logger = logging.Logger(name=__file__)
        self.model_params = ModelParams()
    
    def init_program(self, args=None) -> None:
        self.load_config(args=args)
        self.clear_on_init: bool = args.msg is not None or args.debug
        self.init()

    def init_model_params(self):
        self.model_params.num_ctx = BaseModel.CONTEXT_WINDOW_LARGE

    def init(self) -> None:
        """
        Initializes the program with configuration settings.
        """
        self.model_name: str = ProgramConfig.current.get("MODEL_NAME")
        self.model_chat_name: str = self.model_name.split(":")[0]
        spliced_model_name = self.model_name.split(":")
        self.model_variant = (
            spliced_model_name[1] if len(spliced_model_name) > 1 else None
        )

        self.system_prompt: str = None

        system_file = ProgramConfig.current.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        self.read_system_file(system_file)

        self.chat = Chat()

        self._load_model()
        
        self.init_model_params()
        paths = ProgramConfig.current.get("PATHS")
        self.command_interceptor = ChatCommandInterceptor(self.chat, paths["CHAT_LOG"])
        self.active_executor: CommandExecutor = None


    def process_token(self, token):
        return self.token_processor.process_token(token)

    def clear_process_token(self):
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
        """
        Requests output from the active executor.
        """
        if self.active_executor:
            self.active_executor.output_requested()

    def load_events(self):
        """
        Loads events for the chat and language model.
        """
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
        root: str = os.path.dirname(__file__)
        config_filename: str = os.environ.get(
            "AI_ASSISTANT_CONFIG_FILENAME", default=os.path.join(root, "config.json")
        )

        self.config = ProgramConfig.load()
        if args is None:
            return

        # override with arguments
        if args.model:
            ProgramConfig.current.set(key="MODEL_NAME", value=args.model)

        if args.system:
            system_templates_dir = ProgramConfig.current.get(
                ProgramSetting.PATHS, {}
            ).get(ProgramSetting.SYSTEM_TEMPLATES)
            user_system_templates_dir = ProgramConfig.current.get(
                ProgramSetting.USER_PATHS, {}
            ).get(ProgramSetting.SYSTEM_TEMPLATES)

            filepath: str = os.path.join(
                user_system_templates_dir, args.system.replace(".md", "") + ".md"
            )
            if os.path.exists(filepath):
                ProgramConfig.current.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
            else:
                filepath: str = os.path.join(
                    system_templates_dir, args.system.replace(".md", "") + ".md"
                )
                ProgramConfig.current.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)

        if args.system_file:
            filepath = args.system_file
            if os.path.exists(filepath):
                ProgramConfig.current.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)

        ProgramConfig.current.set(ProgramSetting.PRINT_LOG, args.no_log)
        ProgramConfig.current.set(ProgramSetting.PRINT_OUTPUT, args.no_out)

    def start_chat_loop(self) -> None:
        """
        Runs the program's main loop.
        """
        self.load_events()
        self.chat.loop()

    def read_system_file(self, system_file: str):
        system_templates_dir = ProgramConfig.current.get(ProgramSetting.PATHS, {}).get(
            ProgramSetting.SYSTEM_TEMPLATES
        )
        user_system_templates_dir = ProgramConfig.current.get(
            ProgramSetting.USER_PATHS, {}
        ).get(ProgramSetting.SYSTEM_TEMPLATES)

        system_filepath: str = os.path.join(
            user_system_templates_dir, system_file.replace(".md", "") + ".md"
        )
        user_filepath: str = os.path.join(
            system_templates_dir, system_file.replace(".md", "") + ".md"
        )

        if os.path.exists(system_file):
            return func.read_file(system_file)
        elif os.path.exists(user_filepath):
            return func.read_file(user_filepath)
        elif os.path.exists(system_filepath):
            return func.read_file(system_filepath)
        else:
            return ""

    def _load_model(self) -> BaseModel:
        use_ollama = False
        func.log(f"Checking system :")
        func.log(Color.YELLOW + "  Loading " + self.model_name)
        if use_ollama : 
            self.llm = OllamaModel( self.model_name, system_prompt=self.system_prompt , host=ProgramConfig.current.get(ProgramSetting.OLLAMA_HOST) )
        else:
            # # debug
            self.model_name = "google/gemma-3-4b-it"
            self.llm = HuggingFaceModel(
                self.model_name,
                system_prompt=self.system_prompt,
                host=ProgramConfig.current.get(ProgramSetting.OLLAMA_HOST)
        )
