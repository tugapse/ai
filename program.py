# program.py

import os
import sys
import logging
import json
from datetime import datetime
import threading
from typing import Optional
import argparse

from config import ProgramConfig, ProgramSetting
from core import ChatCommandInterceptor, CommandExecutor
from core.llms import ModelParams, BaseModel, OllamaModel, HuggingFaceModel, T5Model, GGUFImageLLM
from core.template_injection import TemplateInjection
from color import Color, format_text
import functions as func
from core.chat import Chat, ChatRoles

# Import the new HandlerManager
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
        self.command_interceptor = None
        self.llm: Optional[BaseModel] = None
        self.active_executor: CommandExecutor = None
        self.token_processor = ConsoleTokenFormatter()
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None

        self.model_params = ModelParams()
        self.session_chat_filepath: Optional[str] = None
        self.session_timestamp: str = ""

        self.thinking_log_manager: Optional[ThinkingLogManager] = None
        self.output_printer: Optional[OutputPrinter] = None
        # Removed direct references to thinking_handler and file_content_handler here,
        # as they are now managed internally by HandlerManager.
        self.handler_manager: Optional[HandlerManager] = None # NEW: Reference to the manager


    def init_program(self, args: Optional[argparse.Namespace] = None) -> None:
        """
        Initializes program components based on configuration and CLI arguments.
        """
        if self.config is None:
            self.load_config(args=args)

        self.clear_on_init: bool = args.msg is not None if args else False or (
            getattr(args, "debug_console", False) if args else False
        )

        # Initialize core program components (LLM, system prompt, etc.)
        self.init()

        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # --- Chat log setup ---
        chat_log_folder = self.config.get(ProgramSetting.PATHS_CHAT_LOG)
        if chat_log_folder:
            func.ensure_directory_exists(chat_log_folder)
            self.session_chat_filepath = os.path.join(
                chat_log_folder, f"chat_history_{self.session_timestamp}.json"
            )
            func.log(f"INFO: Session chat history will be saved to: {self.session_chat_filepath}")
        else:
            func.log(f"WARNING: Chat log path is not configured. Chat history will not be saved. Check '{ProgramSetting.PATHS_CHAT_LOG}' in your config.", level="WARNING")

        # --- ThinkingLogManager ---
        # This is initialized first as it's a dependency for the HandlerManager.
        thisnk_logs_base_dir = os.path.join(self.config.get(ProgramSetting.PATHS_LOGS),"thinking")
        session_thinking_log_file = f"llm_thinking_{self.session_timestamp}.log"
        if thisnk_logs_base_dir:
            func.ensure_directory_exists(thisnk_logs_base_dir)
            full_thinking_log_path = os.path.join(thisnk_logs_base_dir, session_thinking_log_file)
            self.thinking_log_manager = ThinkingLogManager(log_file_name=full_thinking_log_path)
        else:
            func.log("WARNING: Base logs directory not configured. Thinking logs will not be saved.", level="WARNING")
            self.thinking_log_manager = ThinkingLogManager(log_file_name=None)

        # --- OutputPrinter ---
        # This is also initialized directly here as it's the first stage of token processing,
        # before the HandlerManager's chain.
        print_mode = self.config.get(ProgramSetting.PRINT_MODE, "every_x_tokens")
        tokens_per_print = self.config.get(ProgramSetting.TOKENS_PER_PRINT, 10)
        self.output_printer = OutputPrinter(
            print_mode=print_mode, tokens_per_print=tokens_per_print
        )

        # --- Initialize HandlerManager --- NEW LOGIC
        # The HandlerManager now takes care of initializing its internal handlers
        # (ThinkingAnimationHandler, FileContentHandler) using the necessary config values.
        generated_files_base_path = self.config.get(ProgramSetting.PATHS_WORKSPACES)
        if not generated_files_base_path:
            generated_files_base_path = os.path.join(func.get_root_directory(), "workspaces")
            func.log(f"WARNING: '{ProgramSetting.PATHS_WORKSPACES}' not found in config. Using fallback: {generated_files_base_path}", level="WARNING")

        session_workspace_path = os.path.join(generated_files_base_path, f"session_{self.session_timestamp}")
        func.ensure_directory_exists(session_workspace_path) # Ensure session workspace directory exists

        thinking_mode = self.config.get(ProgramSetting.THINKING_MODE, "progressbar")
        enable_thinking_display = self.config.get(ProgramSetting.ENABLE_THINKING_DISPLAY, True)

        self.handler_manager = HandlerManager(
            log_manager=self.thinking_log_manager,
            output_base_dir=session_workspace_path,
            thinking_mode=thinking_mode,
            enable_thinking_display=enable_thinking_display
        )
        # Removed the direct initialization of self.thinking_handler and self.file_content_handler


    def init_model_params(self):
        """
        Initializes or overrides default ModelParams based on the loaded LLM's properties.
        This ensures model-specific settings from the config file are applied.
        """
        if self.llm and hasattr(self.llm, 'options'):
            model_defaults = ModelParams()
            for key, value in self.llm.options.items():
                # Check if the ModelParams object already has this attribute
                if hasattr(model_defaults, key):
                    self.model_params[ key]= value
                else:
                    func.debug(f"WARNING: Model property '{key}' from LLM options not found in ModelParams. Skipping.")

    def init(self) -> None:
        """
        Initializes core program components like system prompt, LLM, and command interceptor.
        This method assumes `self.config` has already been loaded.
        """
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        self.system_prompt = self.read_system_file(system_file)

        model_config_name_to_load = self.config.get(ProgramSetting.MODEL_CONFIG_NAME)
        self._load_model(model_config_name_to_load)

        if self.llm is None:
            func.log(f"CRITICAL: Failed to load LLM model. Exiting.", level="CRITICAL")
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
            func.log(f"WARNING: '{ProgramSetting.PATHS_LOGS}' not found in config. Using fallback: {logs_path_for_interceptor}", level="WARNING")

        self.command_interceptor = ChatCommandInterceptor(
            self.chat, logs_path_for_interceptor
        )
        self.active_executor: CommandExecutor = None

    def process_token(self, token):
        """
        Processes a token using the ConsoleTokenFormatter (primarily for color).
        This method will now be called with content already filtered by the HandlerManager.
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
        Handles streaming, token processing, and content routing using the HandlerManager.
        """
        started_response = False

        outs = self.llm.chat(
            self.chat.messages,
            stream=True,
            images=self.chat.images,
            options=self.model_params
        )
        try:
            llm_response_accumulated = ""
            for raw_token_string in outs:
                # First, process token through OutputPrinter for buffering/throttling.
                new_token = self.output_printer.process_token(raw_token_string)
                if new_token is None:
                    continue

                # NEW LOGIC: Use the HandlerManager to process the token through the chain.
                # The HandlerManager abstracts away the individual handler calls and their specific returns.
                display_to_user, content_to_display, file_content_saved = \
                    self.handler_manager.process_token_chain(new_token)

                if file_content_saved:
                    # Optional: Add a notification here when a file is saved.
                    # The original code had 'pass', so keeping it the same.
                    pass

                if display_to_user:
                    # If the HandlerManager indicates the token should be displayed to the user.
                    if not started_response:
                        func.out(
                            format_text(self.chat.assistant_prompt, Color.PURPLE)
                            + Color.RESET
                        )
                        started_response = True

                    # Apply console formatting (coloring, etc.) to the content meant for display.
                    formatted_token_for_display = self.token_processor.process_token(
                        content_to_display
                    )

                    # Accumulate for chat history and full response.
                    self.chat.current_message += content_to_display
                    llm_response_accumulated += content_to_display

                    # Print to console.
                    func.out(formatted_token_for_display, end="")

                    # Write to file if external output requested.
                    if (
                        self.write_to_file
                        and self.output_filename
                        and formatted_token_for_display.strip() # Only write if there's non-empty content
                    ):
                        func.write_to_file(
                            self.output_filename,
                            formatted_token_for_display,
                            func.FILE_MODE_APPEND,
                        )

        except Exception as e:
            error_message = f"An error occurred during chat: {e}"
            func.out(f"Error: {error_message}")
            func.out("\n")
            func.log(f"CRITICAL: {error_message}", level="CRITICAL")
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
        Called when the LLM stream finishes. Adds a final newline and clears token processor.
        """
        func.log("Finished LLM Response", level="INFO")
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
        Loads event listeners for chat and LLM events.
        """
        self.chat.add_event(
            event_name=self.chat.EVENT_CHAT_SENT, listener=self.start_chat
        )
        self.chat.add_event(
            event_name=self.chat.EVENT_OUTPUT_REQUESTED, listener=self.output_requested
        )
        if self.llm:
            self.llm.add_event(
                event_name=BaseModel.STREAMING_FINISHED_EVENT,
                listener=self.llm_stream_finished,
            )

    def load_config(self, args: Optional[argparse.Namespace] = None):
        """
        Loads the main program configuration.
        Initializes ProgramConfig singleton and applies CLI overrides.
        """
        self.config = ProgramConfig.load()

        # Apply model config name from CLI args if present
        if args and args.model:
            self.config.set(ProgramSetting.MODEL_CONFIG_NAME, args.model)

        # Handle system prompt arguments
        if args and args.system:
            system_templates_dir = self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES, "")
            filepath: str = os.path.join(
                system_templates_dir, args.system.replace(".md", "") + ".md"
            )
            if os.path.exists(filepath):
                self.config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
            else:
                func.log(f"WARNING: System prompt file '{filepath}' for '{args.system}' not found.", level="WARNING")

        if args and args.system_file:
            filepath = args.system_file
            if os.path.exists(filepath):
                self.config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
            else:
                func.log(f"WARNING: System prompt file '{filepath}' not found.", level="WARNING")

        # Handle no_log and no_out flags
        if args:
            if hasattr(args, "no_log"):
                self.config.set(ProgramSetting.PRINT_LOG, args.no_log)
            if hasattr(args, "no_out"):
                self.config.set(ProgramSetting.PRINT_OUTPUT, args.no_out)


    def start_chat_loop(self) -> None:
        """
        Starts the main interactive chat loop.
        """
        self.load_events()
        self.chat.loop()

    def read_system_file(self, system_file: str) -> str:
        """
        Reads and processes the content of a system prompt file.
        """
        system_templates_dir = self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES)
        system_prompt_content = ""

        if system_file:
            if os.path.exists(system_file):
                func.log(f"INFO: Loaded system file from explicit path: {system_file}", level="INFO")
                system_prompt_content = func.read_file(system_file)
            elif system_templates_dir:
                system_filepath_in_templates = os.path.join(
                    system_templates_dir, system_file.replace(".md", "") + ".md"
                )
                if os.path.exists(system_filepath_in_templates):
                    func.log(f"INFO: Loaded system file from templates directory: {system_filepath_in_templates}", level="INFO")
                    system_prompt_content = func.read_file(system_filepath_in_templates)
                else:
                    func.log(f"WARNING: System prompt file '{system_file}' not found at any known location (explicit path or in templates dir).", level="WARNING")
            else:
                 func.log(f"WARNING: System prompt file '{system_file}' not found and no system templates directory configured.", level="WARNING")

        if len(system_prompt_content) == 0:
            func.log(f"WARNING: No system prompt loaded or found. Continuing without a system prompt.", level="WARNING")

        injection_template = TemplateInjection(system_prompt_content)
        result = injection_template.replace_system_template()
        return result

    def _load_model(self, model_config_name: str) -> BaseModel:
        """
        Loads the LLM model based on the provided model configuration name.
        Reads model properties from the JSON config file.
        """
        func.log(f"INFO: Attempting to load model from config '{model_config_name}'", level="INFO")

        if not model_config_name.endswith(".json"):
            model_config_name += ".json"

        model_configs_folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)

        if not model_configs_folder:
            func.log(f"CRITICAL: '{ProgramSetting.PATHS_MODEL_CONFIGS}' is not configured. Cannot load model. Please set it in config.json or ensure defaults are correct.", level="CRITICAL")
            sys.exit(1)

        func.ensure_directory_exists(model_configs_folder)

        filename = os.path.join(model_configs_folder, model_config_name)

        try:
            with open(filename, "r", encoding="utf-8") as f:
                model_config = json.load(f)
            func.log(f"INFO: Loaded model config from {filename}", level="INFO")
        except FileNotFoundError:
            func.log(f"ERROR: Model configuration file '{filename}' not found. Please ensure it exists in '{model_configs_folder}'.", level="ERROR")
            sys.exit(1)
        except json.JSONDecodeError:
            func.log(f"ERROR: Invalid JSON in '{filename}'. Please check its format.", level="ERROR")
            sys.exit(1)
        except Exception as e:
            func.log(f"ERROR: Failed to load model config from {filename}: {e}", level="ERROR")
            sys.exit(1)

        model_name = model_config.get("model_name")
        model_type = model_config.get("model_type")
        model_properties = model_config.get("model_properties", {})

        # Extract common properties
        max_new_tokens = model_properties.get("max_new_tokens")
        temperature = model_properties.get("temperature")
        top_p = model_properties.get("top_p")
        top_k = model_properties.get("top_k")
        quantization_bits = model_properties.get("quantization_bits", 0)
        n_ctx = model_properties.get("n_ctx")
        n_gpu_layers = model_properties.get("n_gpu_layers", 0)
        verbose = model_properties.get("verbose", False)

        other_llm_kwargs = {k: v for k, v in model_properties.items()
                            if k not in ["quantization_bits", "n_ctx", "n_gpu_layers", "verbose",
                                         "gguf_filename", "model_repo_id",
                                         "max_new_tokens", "temperature", "top_p", "top_k"]
                           }


        if not model_name or not model_type:
            func.log("ERROR: 'model_name' or 'model_type' missing in model configuration. Cannot load model.", level="ERROR")
            sys.exit(1)

        func.log(f"INFO: Selected model: {model_name} (Type: {model_type})", level="INFO")

        self.model_params = ModelParams(
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            quantization_bits=quantization_bits
        ).to_dict()


        if model_type == "causal_lm":
            self.llm = HuggingFaceModel(
                model_name=model_name,
                system_prompt=self.system_prompt,
                quantization_bits=quantization_bits,
                model_params=self.model_params,
                **other_llm_kwargs
            )
            func.log(f"INFO: Model '{model_name}' loaded as a Causal Language Model (HuggingFace).", level="INFO")
        elif model_type == "seq2seq_lm":
            self.llm = T5Model(
                model_name=model_name,
                system_prompt=self.system_prompt,
                quantization_bits=quantization_bits,
                model_params=self.model_params,
                **other_llm_kwargs
            )
            func.log(f"INFO: Model '{model_name}' loaded as a Seq2Seq Language Model (T5-type).", level="INFO")
        elif model_type == "ollama":
            ollama_host = self.config.get(ProgramSetting.OLLAMA_HOST)
            if not ollama_host:
                func.log(f"WARNING: '{ProgramSetting.OLLAMA_HOST}' not configured. Using default Ollama host.", level="WARNING")
                ollama_host = "http://localhost:11434" # Fallback default

            self.llm = OllamaModel(
                model_name=model_name,
                system_prompt=self.system_prompt,
                host=ollama_host,
                model_params=self.model_params,
                **other_llm_kwargs
            )
            func.log(f"INFO: Model '{model_name}' loaded as an Ollama Model.", level="INFO")
        elif model_type == "gguf":
            gguf_filename = model_properties.get("gguf_filename")
            model_repo_id = model_properties.get("model_repo_id")

            if not gguf_filename:
                func.log("ERROR: 'gguf_filename' is required for 'gguf' model_type in model properties.", level="ERROR")
                sys.exit(1)

            self.llm = GGUFImageLLM(
                model_name=model_name,
                gguf_filename=gguf_filename,
                model_repo_id=model_repo_id,
                system_prompt=self.system_prompt,
                n_gpu_layers=n_gpu_layers,
                n_ctx=n_ctx,
                verbose=verbose,
                model_params=self.model_params,
                **other_llm_kwargs
            )
            func.log(f"INFO: Model '{model_name}' loaded as a GGUF Image LLM.", level="INFO")
        else:
            func.log(f"ERROR: Unknown model_type '{model_type}' in model configuration.", level="ERROR")
            sys.exit(1)

        return self.llm

    def _save_chat_history(self):
        """
        Saves the current chat history to the session's JSON file.
        This method is part of the Program class, as it handles configuration (paths).
        """
        if not self.session_chat_filepath:
            func.log(f"WARNING: Session chat file path not initialized. Cannot save chat history.", level="WARNING")
            return

        try:
            with open(self.session_chat_filepath, "w", encoding="utf-8") as f:
                json.dump(self.chat.messages, f, indent=4)
            func.out(" ", flush=True)
            func.log(f"INFO: Chat history saved to {self.session_chat_filepath}", level="INFO")
        except Exception as e:
            func.log(f"ERROR: Failed to save chat history to {self.session_chat_filepath}: {e}", level="ERROR")

