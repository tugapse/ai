import os
import sys
import traceback
from typing import Optional

# Core logic and message types
from core.chat import Chat, ChatRoles
from core.llms.base_llm import BaseModel
from config import ProgramConfig, ProgramSetting

# Services Orchestration
from services.session_manager import SessionManager
from services.prompt_loader import PromptLoader
from services.config_applier import ConfigApplier
from services.event_binder import EventBinder
from services.model_orchestrator import ModelOrchestrator
from services.history_manager import HistoryManager
from services.module_registry import ModuleRegistry
from services.ui_orchestrator import UIOrchestrator
from services.stream_orchestrator import StreamOrchestrator

import functions as func

class Program:
    """
    Main orchestrator for JARVIS. 
    Coordinates services to handle LLM logic, Hardware modules, 
    UI feedback, and Session persistence.
    """

    def __init__(self) -> None:
        self.config: Optional[ProgramConfig] = None
        self.models: Optional[ModelOrchestrator] = None
        self.history: Optional[HistoryManager] = None
        self.modules: Optional[ModuleRegistry] = None
        self.ui: Optional[UIOrchestrator] = None
        self.chat = Chat()

        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self.active_executor = None

    @property
    def llm(self) -> Optional[BaseModel]:
        return self.models.llm

    @property
    def model_params(self) -> dict:
        return self.models.get_params()

    def load_config(self, args=None):
        self.config = ProgramConfig.load()
        self.models = ModelOrchestrator(self.config)
        self.history = HistoryManager(self.chat)
        self.modules = ModuleRegistry(self.config)
        self.ui = UIOrchestrator(self.config)

    def init_program(self, args) -> None:
        ConfigApplier.apply_cli_args_to_config(self.config, args)
        
        if hasattr(args, 'modules') and args.modules:
            for mod_name in args.modules:
                self.config.set(f"{mod_name.upper()}_ENABLED", True)

        session_paths = SessionManager.initialize_session_paths(self.config)
        self.history.initialize_session(session_paths)
        self.ui.initialize(self.history.get_log_path())

        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        system_prompt = PromptLoader.load_system_prompt(self.config, system_file)
        self.models.load(self.config.get(ProgramSetting.MODEL_CONFIG_NAME), system_prompt)
        self.modules.load_all()

    def _handle_tool_call(self, tool_call_string: str):
        self.history.add_message(ChatRoles.ASSISTANT, tool_call_string)
        tool_result = f"<result>\nTool execution confirmed.\n</result>"
        self.history.add_message(ChatRoles.TOOL, tool_result)
        self.history.save()
        self.start_chat(user_input=None)

    def start_chat(self, user_input: Optional[str]):
        """Executes one interaction turn with the LLM and enabled modules."""
        if not self.llm:
            return

        try:
            if user_input and user_input.strip():
                self.history.add_message(ChatRoles.USER, user_input)

            ui_tools = self.ui.get_components()
            
            # Use dictionary access. Wrap in a try/except if 'voice' might not exist in the registry
            voice_mod = None
            try:
                voice_mod = self.modules['voice']
            except (KeyError, TypeError):
                pass
            
            orchestrator = StreamOrchestrator(
                voice_module=voice_mod,
                output_printer=ui_tools["printer"],
                handler_manager=ui_tools["handler"],
                token_processor=ui_tools["formatter"],
                assistant_prompt=self.chat.assistant_prompt,
                debug_voice=False
            )

            stream = self.llm.chat(
                self.chat.messages,
                stream=True,
                options=self.model_params
            )

            result = orchestrator.run(stream)

            # if result.tool_call_detected:
            #     self._handle_tool_call(result.tool_buffer)
            # else:
            if result.accumulated_text:
                self.history.add_message(ChatRoles.ASSISTANT, result.accumulated_text)

        except Exception as e:
            func.log(f"Program: Chat Error: {e}", level="CRITICAL")
            func.log(traceback.format_exc(), level="ERROR")

        finally:
            self.ui.reset_turn()
            
            # Final hardware-level cleanup for the voice module
            try:
                voice = self.modules['voice']
                if voice:
                    voice.collect_audio()
            except:
                pass
            
            self.history.save()
            self.chat.chat_finished()
            func.out("") 

    def run(self) -> None:
        """Main Loop: Binds core events and starts the chat loop."""
        func.log("Program: Interface active.")
        
        EventBinder.bind_core_events(
            chat=self.chat,
            llm=self.llm,
            start_chat_callback=self.start_chat,
            output_requested_callback=lambda: self.active_executor.output_requested() if self.active_executor else None,
            llm_stream_finished_callback=lambda _: None
        )

        try:
            self.chat.loop()
        except KeyboardInterrupt:
            func.log("\nProgram: Shutdown initiated.")
        finally:
            self.modules.shutdown()