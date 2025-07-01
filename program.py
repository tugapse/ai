# program.py

import os
import sys
import logging 
import json
from datetime import datetime
import threading
from typing import Optional
import argparse

# Core components
from config import ProgramConfig, ProgramSetting
from core import ChatCommandInterceptor, CommandExecutor
from core.llms import ModelParams, BaseModel 
from core.chat import Chat, ChatRoles

# Utility/Helper components
from color import Color, format_text
import functions as func

# New/Refactored services
from services.model_manager import ModelManager
from services.session_manager import SessionManager
from services.prompt_loader import PromptLoader
from services.config_applier import ConfigApplier
from services.event_binder import EventBinder

# Extras
from extras import HandlerManager
from extras.thinking_log_manager import ThinkingLogManager
from extras.output_printer import OutputPrinter
from extras import ConsoleTokenFormatter


class Program:
    """
    Main program class for the AI assistant.
    """

    def __init__(self) -> None:
        self.config: Optional[ProgramConfig] = None
        self.model_name: str = "__no_model__"
        self.model_variant = None
        self.system_prompt: str = ""
        self.model_chat_name: str = "__no_chat_name__"
        self.chat = Chat()
        self.command_interceptor: Optional[ChatCommandInterceptor] = None
        self.llm: Optional[BaseModel] = None
        self.active_executor: Optional[CommandExecutor] = None 
        self.token_processor = ConsoleTokenFormatter()
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None

        self.model_params: dict = ModelParams().to_dict()

        # Session-specific paths, managed by SessionManager
        self.session_timestamp: str = ""
        self.session_chat_filepath: Optional[str] = None
        self.session_thinking_log_filepath: Optional[str] = None
        self.session_workspace_path: Optional[str] = None

        self.thinking_log_manager: Optional[ThinkingLogManager] = None
        self.output_printer: Optional[OutputPrinter] = None
        self.handler_manager: Optional[HandlerManager] = None


    def init_program(self, args: Optional[argparse.Namespace] = None) -> None:
        """
        Initializes program components based on configuration and CLI arguments.
        This is the main entry point for setup and now also controls the program's flow.
        """
        # 1. Load Configuration
        self.config = ProgramConfig.load()
        ConfigApplier.apply_cli_args_to_config(self.config, args)

        self.clear_on_init: bool = args.msg is not None if args else False or (
            getattr(args, "debug_console", False) if args else False
        )

        # 2. Initialize Session Paths
        session_paths = SessionManager.initialize_session_paths(self.config)
        
        self.session_timestamp = session_paths["session_timestamp"]
        self.session_chat_filepath = session_paths["session_chat_filepath"]
        self.session_thinking_log_filepath = session_paths["session_thinking_log_filepath"]
        self.session_workspace_path = session_paths["session_workspace_path"]

        # 3. Initialize core program components (LLM, system prompt, etc.)
        self.init() 

        # 4. Setup Logging and Output Managers (now using session_paths)
        self.thinking_log_manager = ThinkingLogManager(log_file_name=self.session_thinking_log_filepath)

        print_mode = self.config.get(ProgramSetting.PRINT_MODE, "line_or_x_tokens")
        tokens_per_print = self.config.get(ProgramSetting.TOKENS_PER_PRINT, 20)
        self.output_printer = OutputPrinter(
            print_mode=print_mode, tokens_per_print=tokens_per_print
        )

        thinking_mode = self.config.get(ProgramSetting.THINKING_MODE, "progressbar")
        enable_thinking_display = self.config.get(ProgramSetting.ENABLE_THINKING_DISPLAY, True)

        self.handler_manager = HandlerManager(
            log_manager=self.thinking_log_manager,
            output_base_dir=self.session_workspace_path,
            thinking_mode=thinking_mode,
            enable_thinking_display=enable_thinking_display
        )
        self.config.save_config()


    def init_model_params(self):
        """
        Initializes or overrides default ModelParams based on the loaded LLM's properties.
        This ensures model-specific settings from the config file are applied.
        """
        if self.llm and hasattr(self.llm, 'options'):
            self.model_params = ModelParams(**self.llm.options).to_dict()
        else:
            self.model_params = ModelParams().to_dict()

    def init(self) -> None:
        """
        Initializes core program components like system prompt, LLM, and command interceptor.
        """
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        self.system_prompt = PromptLoader.load_system_prompt(self.config, system_file)

        model_config_name_to_load = self.config.get(ProgramSetting.MODEL_CONFIG_NAME)
        self._load_model(model_config_name_to_load)

        if self.llm is None:
            func.log(f"Failed to load LLM model. Exiting.", level="CRITICAL") 
            sys.exit(1)

        self.model_name = self.llm.model_name
        spliced_model_name = self.model_name.split(":")
        self.model_chat_name: str = spliced_model_name[0]
        self.model_variant = (
            spliced_model_name[1] if len(spliced_model_name) > 1 else None
        )

        self.init_model_params()

        logs_path_for_interceptor = self.config.get(ProgramSetting.PATHS_LOGS)
        if not logs_path_for_interceptor:
            logs_path_for_interceptor = os.path.join(func.get_root_directory(), "logs")
            func.log(f"'{ProgramSetting.PATHS_LOGS}' not found in config. Using fallback: {logs_path_for_interceptor}", level="WARNING") 

        self.command_interceptor = ChatCommandInterceptor(
            self.chat, logs_path_for_interceptor
        )


    def process_token(self, token):
        """
        Processes a token using the ConsoleTokenFormatter (primarily for color).
        """
        return self.token_processor.process_token(token)

    def clear_process_token(self):
        """
        Clears the internal state of ConsoleTokenFormatter.
        """
        self.token_processor.clear_process_token()

    def start_chat(self, user_input):
        """
        Initiates the LLM chat session for a given user input.
        """
        started_response = False

        if self.llm is None:
            func.log("LLM is not initialized. Cannot start chat.", level="CRITICAL") 
            return

        outs = self.llm.chat(
            self.chat.messages,
            stream=True,
            images=self.chat.images,
            options=self.model_params
        )
        try:
            llm_response_accumulated = ""
            for raw_token_string in outs:
                new_token = self.output_printer.process_token(raw_token_string)
                if new_token is None:
                    continue

                display_to_user, content_to_display, file_content_saved = \
                    self.handler_manager.process_token_chain(new_token)

                if file_content_saved:
                    pass

                if display_to_user:
                    if not started_response:
                        func.out( # Confirmed func.out
                            format_text(self.chat.assistant_prompt, Color.PURPLE)
                            + Color.RESET, end="" 
                        )
                        started_response = True

                    formatted_token_for_display = self.token_processor.process_token(
                        content_to_display
                    )

                    self.chat.current_message += content_to_display
                    llm_response_accumulated += content_to_display

                    func.out(formatted_token_for_display, end="") # Confirmed func.out

                    if (
                        self.write_to_file
                        and self.output_filename
                        and formatted_token_for_display.strip()
                    ):
                        func.write_to_file( 
                            self.output_filename,
                            formatted_token_for_display,
                            func.FILE_MODE_APPEND,
                        )

        except Exception as e:
            error_message = f"An error occurred during chat: {e}"
            func.out(f"Error: {error_message}") # Confirmed func.out
            func.out("\n") # Confirmed func.out
            func.log(f"{error_message}", level="CRITICAL") 
            import traceback
            func.log(f"Traceback:\n{traceback.format_exc()}", level="ERROR") 
            llm_response_accumulated = f"ERROR: {error_message}"

        finally:
            if self.output_printer:
                self.output_printer.flush_buffers()

            if llm_response_accumulated:
                self.chat.messages.append(
                    BaseModel.create_message(
                        ChatRoles.ASSISTANT, llm_response_accumulated.strip()
                    )
                )

            self._save_chat_history()
            self.llm_stream_finished()

    def llm_stream_finished(self, data=""):
        """
        Called when the LLM stream finishes.
        """
        func.log("Finished LLM Response") 
        self.clear_process_token()
        self.chat.chat_finished()

    def output_requested(self):
        """
        Handles requests for output from the active command executor.
        """
        if self.active_executor:
            self.active_executor.output_requested()

    def load_events(self):
        """
        Loads event listeners for chat and LLM events using EventBinder.
        """
        EventBinder.bind_core_events(
            chat=self.chat,
            llm=self.llm,
            start_chat_callback=self.start_chat,
            output_requested_callback=self.output_requested,
            llm_stream_finished_callback=self.llm_stream_finished
        )

    def load_config(self, args: Optional[argparse.Namespace] = None):
        """
        Loads the main program configuration.
        """
        self.config = ProgramConfig.load()


    def start_chat_loop(self) -> None:
        """
        Starts the main interactive chat loop.
        """
        self.load_events()
        self.chat.loop()

    def read_system_file(self, system_file: str) -> str:
        """
        Reads and processes the content of a system prompt file using PromptLoader.
        """
        return PromptLoader.load_system_prompt(self.config, system_file)

    def _load_model(self, model_config_name: str) -> None:
        """
        Loads the LLM model configuration and instantiates the model
        using ModelManager.
        """
        func.log(f"Attempting to load model from config '{model_config_name}'") 

        if not model_config_name.endswith(".json"):
            model_config_name += ".json"

        model_configs_folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)

        if not model_configs_folder:
            func.log(f"'{ProgramSetting.PATHS_MODEL_CONFIGS}' is not configured. Cannot load model. Please set it in config.json or ensure defaults are correct.", level="CRITICAL") 
            sys.exit(1)

        func.ensure_directory_exists(model_configs_folder)

        filename = os.path.join(model_configs_folder, model_config_name)

        model_config = None
        try:
            model_config = ModelManager.load_config(filename) 
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            func.log(f"Failed to load model config from {filename}: {e}", level="CRITICAL") 
            sys.exit(1)

        model_type_from_config = model_config.get("model_type")

        ollama_host = None
        if model_type_from_config == "ollama":
            ollama_host = self.config.get(ProgramSetting.OLLAMA_HOST)
            if not ollama_host:
                func.log(f"'{ProgramSetting.OLLAMA_HOST}' not configured. Using default Ollama host.", level="WARNING") 
                ollama_host = "http://localhost:11434"

        self.llm = ModelManager.load_model_instance(
            model_config=model_config,
            system_prompt=self.system_prompt,
            ollama_host=ollama_host
        )

        if self.llm is None:
            func.log("LLM model could not be instantiated. Exiting.", level="CRITICAL") 
            sys.exit(1)


    def _save_chat_history(self):
        """
        Saves the current chat history to the session's JSON file.
        """
        if not self.session_chat_filepath:
            func.log(f"Session chat file path not initialized. Cannot save chat history.", level="WARNING") 
            return

        try:
            with open(self.session_chat_filepath, "w", encoding="utf-8") as f:
                json.dump(self.chat.messages, f, indent=4)
            func.out(" ", flush=True) 
            func.log(f"Chat history saved to {self.session_chat_filepath}") 
        except Exception as e:
            func.log(f"Failed to save chat history to {self.session_chat_filepath}: {e}", level="ERROR") 
