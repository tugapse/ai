import os
import sys
import logging
import json
from datetime import datetime

from config import ProgramConfig, ProgramSetting
from core import Chat, ChatCommandInterceptor, CommandExecutor
from core.llms import ModelParams, BaseModel, OllamaModel, HuggingFaceModel, T5Model
from color import Color, format_text
import functions as func
from extras import ConsoleTokenFormatter

# --- New Imports for Thinking Logic and Output Control ---
from core.llms.think_parser import ThinkingAnimationHandler
from core.llms.thinking_log_manager import ThinkingLogManager
from core.llms.output_printer import OutputPrinter
# --- End New Imports ---

class Program:
    """
    Main program class for the AI assistant.
    """
    def __init__(self) -> None:
        self.config: ProgramConfig = None
        self.model_name: str = "__no_model__"
        self.model_variant = None
        self.system_prompt: str = None
        self.model_chat_name: str = None
        self.chat = Chat()
        self.command_interceptor = None
        self.llm: BaseModel = None
        self.active_executor: CommandExecutor = None
        self.token_processor = ConsoleTokenFormatter()
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self._logger = logging.Logger(name=__file__)
        self.model_params = ModelParams()
        self.session_chat_filepath = None

        # --- New: Initialize thinking and output related attributes as None ---
        self.thinking_log_manager: ThinkingLogManager = None
        self.thinking_handler: ThinkingAnimationHandler = None
        self.output_printer: OutputPrinter = None
        # --- End New Attributes ---

    def init_program(self, args=None) -> None:
        self.load_config(args=args)
        self.clear_on_init: bool = args.msg is not None or (getattr(args, 'debug_console', False) if args else False)
        
        # Ensure self.init() runs BEFORE initializing components that depend on ProgramConfig values.
        self.init()
        
        # --- Existing chat log setup ---
        chat_log_folder = self.config.get(ProgramSetting.PATHS_CHAT_LOG)
        if chat_log_folder:
            os.makedirs(chat_log_folder, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_chat_filepath = os.path.join(chat_log_folder, f"chat_history_{timestamp}.json")
            func.log(f"INFO: Session chat history will be saved to: {self.session_chat_filepath}")
        else:
            func.log(f"WARNING: Chat log path is not configured. Chat history will not be saved. Check '{ProgramSetting.PATHS_CHAT_LOG}' in your config.")

        # --- New: Initialize ThinkingLogManager ---
        # Log file name can be configurable, default to "llm_thinking.log"
        log_file_name = self.config.get(ProgramSetting.LLM_THINKING_LOG_FILE, "llm_thinking.log")
        self.thinking_log_manager = ThinkingLogManager(log_file_name=log_file_name)

        # --- New: Initialize ThinkingAnimationHandler ---
        # Get settings from config, with sensible defaults
        thinking_mode = self.config.get(ProgramSetting.THINKING_MODE, "spinner")
        enable_thinking_display = self.config.get(ProgramSetting.ENABLE_THINKING_DISPLAY, True)
        self.thinking_handler = ThinkingAnimationHandler(
            enable_display=enable_thinking_display,
            mode=thinking_mode,
            log_manager=self.thinking_log_manager
        )

        # --- New: Initialize OutputPrinter for flexible output modes ---
        # Get settings from config, with sensible defaults
        print_mode = self.config.get(ProgramSetting.PRINT_MODE, "token")
        tokens_per_print = self.config.get(ProgramSetting.TOKENS_PER_PRINT, 5)
        self.output_printer = OutputPrinter(
            print_mode=print_mode,
            tokens_per_print=tokens_per_print
        )
        # --- End New Initializations ---

    def init_model_params(self):
        self.model_params.num_ctx = BaseModel.CONTEXT_WINDOW_LARGE

    def init(self) -> None:
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        self.system_prompt = self.read_system_file(system_file) 

        model_config_name_to_load = ProgramConfig.current.get("MODEL_CONFIG_NAME")
        self._load_model(model_config_name_to_load)
        
        if self.llm is None or self.llm.model is None:
            func.log(f"CRITICAL: Failed to load LLM model. Exiting.")
            sys.exit(1)

        self.model_name = self.llm.model_name 
        spliced_model_name = self.model_name.split(":")
        self.model_chat_name: str = spliced_model_name[0]
        self.model_variant = spliced_model_name[1] if len(spliced_model_name) > 1 else None

        self.init_model_params()
        self.command_interceptor = ChatCommandInterceptor(self.chat, self.config.get(ProgramSetting.PATHS_CHAT_LOG))
        self.active_executor: CommandExecutor = None


    def process_token(self, token):
        """
        Processes a token using the ConsoleTokenFormatter (primarily for color).
        This method will now be called with content already filtered by ThinkingAnimationHandler.
        """
        return self.token_processor.process_token(token)

    def clear_process_token(self):
        """
        Clears the internal state of ConsoleTokenFormatter.
        """
        self.token_processor.clear_process_token()

    def start_chat(self, user_input):
        started_response = False
        
        generation_options = self.model_params.to_dict()

        outs = self.llm.chat(
            self.chat.messages,
            images=self.chat.images,
            options=generation_options,
        )
        try:
            llm_response_accumulated = ""
            for raw_token_string in outs: # Iterate through raw tokens from the LLM stream
                # --- New: Process raw token through the thinking handler first ---
                # This filters <think> tags, displays animation, and logs internal thoughts.
                is_thinking, content_for_display = self.thinking_handler.process_token_and_thinking_state(raw_token_string)

                # Only proceed with printing and accumulation if NOT thinking AND there's content to display
                if not is_thinking and content_for_display:
                    if not started_response:
                        func.out(
                            format_text(self.chat.assistant_prompt, Color.PURPLE) + Color.RESET,
                            end=" ",
                        )
                        started_response = True

                    # Format token with ConsoleTokenFormatter (e.g., applying color)
                    formatted_token_for_display = self.token_processor.process_token(content_for_display)
                    
                    # Accumulate ONLY the displayable content for chat history and current message
                    self.chat.current_message += content_for_display
                    llm_response_accumulated += content_for_display

                    # Print using the OutputPrinter for buffering and output modes (token, line, every_x_tokens)
                    self.output_printer.process_and_print(formatted_token_for_display)

                    # If writing to a file, also filter by displayable content
                    if self.write_to_file and self.output_filename and formatted_token_for_display:
                        func.write_to_file(self.output_filename, formatted_token_for_display, func.FILE_MODE_APPEND)
                # If is_thinking or content_for_display is empty, do nothing with it for console output.
                # The thinking_handler takes care of displaying the animation and logging.

        except Exception as e:
            error_message = f"An error occurred during chat: {e}"
            func.out(f"Error: {error_message}\n")
            func.out("\n")
            print(f"\nCRITICAL: {error_message}")
            import traceback
            traceback.print_exc()
            self.running = False
            llm_response_accumulated = f"ERROR: {error_message}" # Still add error to accumulated for history if desired

        finally:
            # --- New: IMPORTANT: Flush any remaining buffered output from OutputPrinter. ---
            # This ensures all buffered tokens are printed to console at the end of the stream
            # (even if an error occurred or the stream finished abruptly).
            if self.output_printer: # Defensive check
                self.output_printer.flush_buffers()

            # The ThinkingAnimationHandler's `process_token_and_thinking_state` and the `</think>` tag
            # handle clearing the thinking animation line and adding a newline. So, no explicit action
            # is typically needed here for thinking display cleanup, unless an unexpected termination
            # happens mid-thought without a </think> tag.

            # Append only the accumulated, user-displayable response to chat messages
            if llm_response_accumulated:
                self.chat.messages.append(BaseModel.create_message("assistant", llm_response_accumulated.strip()))
            
            self._save_chat_history() # Save chat history with only the clean output
            self.llm_stream_finished() # This method will add the final newline and clean up chat state.


    def llm_stream_finished(self, data=""):
        func.out("\n") # Adds a final newline after the LLM's complete response
        self.clear_process_token() # Clears any internal state of the ConsoleTokenFormatter
        self.chat.chat_finished()

    def output_requested(self):
        if self.active_executor:
            self.active_executor.output_requested()

    def load_events(self):
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
        self.config = ProgramConfig.load()

        if args is None:
            ProgramConfig.current.set(key="MODEL_CONFIG_NAME", value="default_model_config.json")
            return

        if args.model: 
            ProgramConfig.current.set(key='MODEL_CONFIG_NAME', value=args.model)
        else:
            ProgramConfig.current.set(key="MODEL_CONFIG_NAME", value="default_model_config.json")

        if args.system:
            system_templates_dir = self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES, "")
            filepath: str = os.path.join(
                system_templates_dir, args.system.replace(".md", "") + ".md"
            )
            if os.path.exists(filepath):
                self.config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
            else:
                func.log(f"WARNING: System prompt file '{filepath}' for '{args.system}' not found.")
           
        if args.system_file:
            filepath = args.system_file
            if os.path.exists(filepath):
                self.config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
            else:
                func.log(f"WARNING: System prompt file '{filepath}' not found.")

        # Updated to use .get with default values, ensuring consistency
        self.config.set(ProgramSetting.PRINT_LOG, args.no_log if hasattr(args, 'no_log') else self.config.get(ProgramSetting.PRINT_LOG, True))
        self.config.set(ProgramSetting.PRINT_OUTPUT, args.no_out if hasattr(args, 'no_out') else self.config.get(ProgramSetting.PRINT_OUTPUT, True))

        # --- New: Handle command line arguments for new settings if you add them ---
        # Example if you want to allow setting these from command line:
        # if hasattr(args, 'thinking_mode') and args.thinking_mode is not None:
        #     self.config.set(ProgramSetting.THINKING_MODE, args.thinking_mode)
        # if hasattr(args, 'print_mode') and args.print_mode is not None:
        #     self.config.set(ProgramSetting.PRINT_MODE, args.print_mode)
        # if hasattr(args, 'tokens_per_print') and args.tokens_per_print is not None:
        #     self.config.set(ProgramSetting.TOKENS_PER_PRINT, int(args.tokens_per_print))
        # if hasattr(args, 'enable_thinking_display') and args.enable_thinking_display is not None:
        #     self.config.set(ProgramSetting.ENABLE_THINKING_DISPLAY, args.enable_thinking_display)
        # if hasattr(args, 'llm_thinking_log_file') and args.llm_thinking_log_file is not None:
        #     self.config.set(ProgramSetting.LLM_THINKING_LOG_FILE, args.llm_thinking_log_file)
        # --- End New Argument Handling ---


    def start_chat_loop(self) -> None:
        self.load_events()
        self.chat.loop()

    def read_system_file(self, system_file: str) -> str:
        system_templates_dir = self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES)
        
        if system_file and os.path.exists(system_file):
            return func.read_file(system_file)
        
        if system_templates_dir and system_file:
            system_filepath = os.path.join(system_templates_dir, system_file.replace(".md","") + ".md")
            if os.path.exists(system_filepath):
                return func.read_file(system_filepath)
        
        func.log(f"WARNING: System prompt file '{system_file}' not found at any known location.")
        return ""

    def _load_model(self, model_config_name: str) -> BaseModel:
        
        func.log(f"Starting system :")
       
        
        if not model_config_name.endswith(".json"):
            model_config_name += ".json"

        model_configs_folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
        if not model_configs_folder:
            model_configs_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_configs") 
            if not os.path.exists(model_configs_folder):
                os.makedirs(model_configs_folder, exist_ok=True)
                func.log(f"INFO: Created default model configs folder at {model_configs_folder}")

        filename = os.path.join(model_configs_folder, model_config_name)

        try:
            with open(filename, 'r') as f:
                model_config = json.load(f)
            func.log(f"INFO: Loaded model config from {filename}")
        except FileNotFoundError:
            func.log(f"ERROR: Model configuration file '{filename}' not found.")
            func.log("Please ensure the file exists in the specified PATHS_MODEL_CONFIGS or create it.")
            sys.exit(1)
        except json.JSONDecodeError:
            func.log(f"ERROR: Invalid JSON in '{filename}'. Please check its format.")
            sys.exit(1)
        except Exception as e:
            func.log(f"ERROR: Failed to load model config from {filename}: {e}")
            sys.exit(1)

        model_name = model_config.get("model_name")
        model_type = model_config.get("model_type")
        model_properties = model_config.get("model_properties", {})
        
        quantization_bits = model_properties.get("quantization_bits", 0)

        if not model_name or not model_type:
            func.log("ERROR: 'model_name' or 'model_type' missing in model configuration.")
            sys.exit(1)

        func.log(Color.YELLOW + f"INFO: Selected model: {model_name} (Type: {model_type})")

        if model_type == "causal_lm":
            self.llm = HuggingFaceModel(
                model_name=model_name,
                system_prompt=self.system_prompt,
                quantization_bits=quantization_bits
            )
            func.log(f"INFO: Model '{model_name}' loaded as a Causal Language Model (HuggingFace).")
        elif model_type == "seq2seq_lm":
            self.llm = T5Model(
                model_name=model_name,
                system_prompt=self.system_prompt,
                quantization_bits=quantization_bits
            )
            func.log(f"INFO: Model '{model_name}' loaded as a Seq2Seq Language Model (T5-type).")
        elif model_type == "ollama":
            self.llm = OllamaModel(
                model_name=model_name,
                system_prompt=self.system_prompt,
                host=self.config.get(ProgramSetting.OLLAMA_HOST)
            )
            func.log(f"INFO: Model '{model_name}' loaded as an Ollama Model.")
        else:
            func.log(f"ERROR: Unknown model_type '{model_type}' in model configuration.")
            sys.exit(1)

        if self.llm and hasattr(self.llm, 'options') and isinstance(self.llm.options, ModelParams):
            for key, value in model_properties.items():
                if hasattr(self.llm.options, key):
                    setattr(self.llm.options, key, value)
                else:
                    func.log(f"WARNING: Unknown model property '{key}' for model type '{model_type}'. Skipping.")
                    
        return self.llm

    def _save_chat_history(self):
        """
        Saves the current chat history to the session's JSON file.
        This method is part of the Program class, as it handles configuration (paths).
        """
        if not self.session_chat_filepath:
            func.log(f"WARNING: Session chat file path not initialized. Cannot save chat history.")
            return

        try:
            with open(self.session_chat_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.chat.messages, f, indent=4)
            func.log(f"INFO: Chat history saved to {self.session_chat_filepath}")
        except Exception as e:
            func.log(f"ERROR: Failed to save chat history to {self.session_chat_filepath}: {e}")
