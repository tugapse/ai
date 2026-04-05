import os
import re
import sys
import json
import argparse
import traceback
import unicodedata
from typing import Optional

# Core components
from config import ProgramConfig, ProgramSetting
from core import ChatCommandInterceptor, CommandExecutor
from core.llms.base_llm import ModelParams, BaseModel 
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

from agents.agent import MessageOrchestrator, LLMConnector, ToolRegistry, load_pipeline_config
import agents.agent_tools as agent_tools

class Program:
    """
    Main program class for the AI assistant. 
    Hardened for Qwen3 stability and clean CLI exit.
    """

    def __init__(self) -> None:
        self.config: ProgramConfig = ProgramConfig()
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

        # Session-specific paths
        self.session_timestamp: str = ""
        self.session_chat_filepath: Optional[str] = None
        self.session_thinking_log_filepath: Optional[str] = None
        self.session_workspace_path: Optional[str] = None

        self.thinking_log_manager: Optional[ThinkingLogManager] = None
        self.output_printer: Optional[OutputPrinter] = None
        self.handler_manager: Optional[HandlerManager] = None

    def load_config(self, args: Optional[argparse.Namespace] = None):
        """Loads the main program configuration."""
        self.config = ProgramConfig.load()

    def init_program(self, args: Optional[argparse.Namespace]) -> None:
        """Initializes components based on configuration and CLI arguments."""
        if not self.config:
            self.load_config(args)
            
        ConfigApplier.apply_cli_args_to_config(self.config, args)

        self.clear_on_init = args.msg is not None if args else False
        
        session_paths = SessionManager.initialize_session_paths(self.config)
        self.session_timestamp = session_paths["session_timestamp"]
        self.session_chat_filepath = session_paths["session_chat_filepath"]
        self.session_thinking_log_filepath = session_paths["session_thinking_log_filepath"]
        self.session_workspace_path = session_paths["session_workspace_path"]

        self.init() 

        self.thinking_log_manager = ThinkingLogManager(log_file_name=self.session_thinking_log_filepath)

        self.output_printer = OutputPrinter(
            print_mode=self.config.get(ProgramSetting.PRINT_MODE, "line_or_x_tokens"),
            tokens_per_print=self.config.get(ProgramSetting.TOKENS_PER_PRINT, 20)
        )

        self.handler_manager = HandlerManager(
            log_manager=self.thinking_log_manager,
            thinking_mode=self.config.get(ProgramSetting.THINKING_MODE, "progressbar"),
            enable_thinking_display=self.config.get(ProgramSetting.ENABLE_THINKING_DISPLAY, True),
            show_thinking_animation=True
        )

    def init_model_params(self):
        if self.llm and hasattr(self.llm, 'options'):
            self.model_params = ModelParams(**self.llm.options).to_dict()
        else:
            self.model_params = ModelParams().to_dict()

    def init(self) -> None:
        func.log("Program: Core init...")
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        self.system_prompt = self.read_system_file(system_file)

        model_config_name_to_load = self.config.get(ProgramSetting.MODEL_CONFIG_NAME)
        self._load_model(model_config_name_to_load)

        if self.llm is None:
            func.error("Program: LLM could not be loaded.", level="CRITICAL") 
            sys.exit(1)

        self.model_name = self.llm.model_name
        self.init_model_params()

        logs_path = self.config.get(ProgramSetting.PATHS_LOGS) or os.path.join(func.get_root_directory(), "logs")
        self.command_interceptor = ChatCommandInterceptor(self.chat, logs_path)

    def read_system_file(self, system_file: str) -> str:
        return PromptLoader.load_system_prompt(self.config, system_file)

    def process_token(self, token):
        return self.token_processor.process_token(token)

    def clear_process_token(self):
        self.token_processor.clear_process_token()

    def output_requested(self):
        if self.active_executor:
            self.active_executor.output_requested()

    def _handle_tool_call(self, tool_call_string: str):
        func.log(f"Program: Handling tool call: {tool_call_string}", level="INFO")

        # For now, we'll just log the tool call and add a placeholder result.
        # In a real scenario, you would parse this and execute the tool.
        tool_name = "unknown_tool"
        # Basic parsing to find tool name
        try:
            lines = tool_call_string.strip().split('\n')
            if len(lines) > 1:
                tool_name = lines[1].strip()
        except Exception as e:
            func.log(f"Could not parse tool name from call: {e}", level="WARN")

        # Add the original tool call message from the assistant
        self.chat.messages.append(
            BaseModel.create_message(ChatRoles.ASSISTANT, tool_call_string)
        )

        # Add a placeholder tool result message
        tool_result_content = f"<result>\nTool '{tool_name}' executed successfully.\n</result>"
        self.chat.messages.append(
            BaseModel.create_message(ChatRoles.TOOL, tool_result_content)
        )

        # Save history and trigger a new turn to process the result
        self._save_chat_history()
        func.log("Program: Tool call handled. Triggering next AI turn.")
        self.start_chat(user_input=None) # Pass None to indicate it's a continuation

    def start_chat(self, user_input: Optional[str]):
        # State machine for stream processing
        STREAM_STATE_NORMAL = "normal"
        STREAM_STATE_TOOL_CAPTURE = "tool_capture"
        
        # Initialization
        stream_state = STREAM_STATE_NORMAL
        started_response = False
        llm_response_accumulated = ""
        tool_buffer = ""
        is_first_token = True

        if self.llm is None:
            func.log("Program: LLM is None, cannot chat.", level="CRITICAL")
            return

        try:
            func.log("Program: LLM Chat starting...")
            outs = self.llm.chat(
                self.chat.messages,
                stream=True,
                images=self.chat.images,
                options=self.model_params
            )

            for raw_token_string in outs:
                # 1. Sanitize Token ("Clean-Pipe")
                sanitized_token = unicodedata.normalize('NFKC', raw_token_string)
                sanitized_token = re.sub(r'[^\x20-\x7E\n\t]', '', sanitized_token)

                if not sanitized_token:
                    continue

                # 2. State Transition and Buffering Logic
                if is_first_token:
                    is_first_token = False
                    if sanitized_token.strip().startswith("<tool>"):
                        func.log("Program: Tool mode detected.", level="INFO")
                        stream_state = STREAM_STATE_TOOL_CAPTURE
                
                if stream_state == STREAM_STATE_TOOL_CAPTURE:
                    tool_buffer += sanitized_token
                    if "</tool>" in tool_buffer:
                        end_tag_index = tool_buffer.find("</tool>") + len("</tool>")
                        final_tool_call = tool_buffer[:end_tag_index]
                        
                        self._handle_tool_call(final_tool_call)
                        return # End this chat turn; the tool handler will start the next one
                    continue

                # 3. Normal Processing (if not in tool mode)
                new_token = self.output_printer.process_token(sanitized_token)
                if new_token is None:
                    continue

                display_to_user, content_to_display, _ = self.handler_manager.process_token_chain(new_token)

                if display_to_user:
                    if not started_response:
                        func.out(format_text(self.chat.assistant_prompt, Color.PURPLE) + Color.RESET, end="")
                        started_response = True

                    formatted_token = self.token_processor.process_token(content_to_display)
                    self.chat.current_message += content_to_display
                    llm_response_accumulated += content_to_display
                    func.out(formatted_token, end="")

            func.log("Program: Stream iterator finished.")

        except Exception as e:
            func.log(f"Program: Error in start_chat: {e}", level="CRITICAL")
            func.log(f"Traceback:\n{traceback.format_exc()}", level="ERROR")
            llm_response_accumulated = f"ERROR: {e}"

        finally:
            # This finally block only runs for NORMAL responses or errors.
            # Tool calls will `return` early from the function.
            if stream_state == STREAM_STATE_NORMAL:
                if self.output_printer:
                    self.output_printer.flush_buffers()

                if llm_response_accumulated:
                    self.chat.messages.append(
                        BaseModel.create_message(ChatRoles.ASSISTANT, llm_response_accumulated.strip())
                    )

                self._save_chat_history()
                self.llm_stream_finished()

    def llm_stream_finished(self, data=""):
        func.log("Program: Stream finished.") 
        func.out("") 
        self.clear_process_token()
        self.chat.chat_finished()

    def run_agent_flow(self, user_prompt: str):
        func.log("Program: Starting Agent Orchestrator...")
        pipeline_config = load_pipeline_config(self, "pipelines/pipeline.json")
        if not pipeline_config:
            func.error("Program: Missing pipeline config.")
            return

        connector = LLMConnector(self.llm)
        registry = ToolRegistry()
        for name, tool_ref in agent_tools.AVAILABLE_TOOLS.items():
            registry.register_tool(name, tool_ref)

        orchestrator = MessageOrchestrator(
            connector=connector, registry=registry, pipeline_config=pipeline_config
        )

        try:
            orchestrator.run_loop(user_prompt)
        except Exception as e:
            func.error(f"Program: Orchestrator error: {e}")
        finally:
            func.log("Program: Agent Flow finished.")

    def load_events(self):
        EventBinder.bind_core_events(
            chat=self.chat,
            llm=self.llm,
            start_chat_callback=self.start_chat,
            output_requested_callback=self.output_requested,
            llm_stream_finished_callback=self.llm_stream_finished
        )
        self.chat.add_event(self.chat.EVENT_AGENT_RUN_REQUESTED, self.run_agent_flow)

    def _load_model(self, model_config_name: str) -> None:
        func.log(f"Program: Loading model {model_config_name}") 
        if not model_config_name.endswith(".json"):
            model_config_name += ".json"

        folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
        filename = os.path.join(folder, model_config_name)

        try:
            model_config = ModelManager.load_config(filename) 
            self.model_chat_name = model_config.get("model_name", self.model_chat_name)
            self.llm = ModelManager.load_model_instance(
                model_config=model_config,
                system_prompt=self.system_prompt,
                ollama_host=self.config.get(ProgramSetting.OLLAMA_HOST)
            )
        except Exception as e:
            func.error(f"Program: Load model error: {e}", level="CRITICAL") 
            sys.exit(1)

    def _save_chat_history(self):
        if not self.session_chat_filepath:
            return
        try:
            with open(self.session_chat_filepath, "w", encoding="utf-8") as f:
                json.dump(self.chat.messages, f, indent=4)
        except Exception as e:
            func.log(f"Program: Failed to save history: {e}", level="ERROR")

    def cleanup(self):
        func.log("Program: Running cleanup...")
        if self.llm and hasattr(self.llm, 'close'):
            self.llm.close()

    def run(self) -> None:
        func.log("Program: Main loop starting.")
        self.load_events()
        try:
            self.chat.loop()
        finally:
            self.cleanup()
            func.log("Program: Forcing OS exit to bypass Segfault.")
            os._exit(0)

if __name__ == "__main__":
    p = Program()
    p.run()