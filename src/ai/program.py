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
        # Config and services are initialized in load_config()
        self.config: Optional[ProgramConfig] = None
        self.models: Optional[ModelOrchestrator] = None
        self.history: Optional[HistoryManager] = None
        self.modules: Optional[ModuleRegistry] = None
        self.ui: Optional[UIOrchestrator] = None

        self.chat = Chat()

        # Attributes for compatibility with existing CLI processors
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self.active_executor = None

    @property
    def llm(self) -> Optional[BaseModel]:
        """Provides direct access to the active LLM instance."""
        return self.models.llm

    @property
    def model_chat_name(self) -> str:
        """Returns the display name of the current model."""
        return self.models.get_chat_name()

    @property
    def model_params(self) -> dict:
        """Returns the sampling parameters (temp, top_p, etc.)."""
        return self.models.get_params()

    def load_config(self, args=None):
        """
        Loads the configuration from disk and initializes all core services.
        This ensures all services share the same, correct config reference.
        """
        self.config = ProgramConfig.load()

        # Service Initialization
        self.models = ModelOrchestrator(self.config)
        self.history = HistoryManager(self.chat)
        self.modules = ModuleRegistry(self.config)
        self.ui = UIOrchestrator(self.config)

    def init_program(self, args) -> None:
        """
        Processes flags and boots hardware.
        This must happen before CliArgs.parse_args.
        """
        # 1. Sync CLI args to the config object
        ConfigApplier.apply_cli_args_to_config(self.config, args)
        
        # 2. Process --modules flag BEFORE the registry loads
        if hasattr(args, 'modules') and args.modules:
            for mod_name in args.modules:
                config_key = f"{mod_name.upper()}_ENABLED"
                self.config.set(config_key, True)
                # Use func.log so it appears in your -pdb logs
                func.log(f"Program: Internal flag set: {config_key}=True")

        # 3. Standard Init
        session_paths = SessionManager.initialize_session_paths(self.config)
        self.history.initialize_session(session_paths)
        self.ui.initialize(self.history.get_log_path())

        # 4. Load AI
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        system_prompt = PromptLoader.load_system_prompt(self.config, system_file)
        self.models.load(self.config.get(ProgramSetting.MODEL_CONFIG_NAME), system_prompt)

        # 5. Boot Modules (Now they will see the True flags)
        self.modules.load_all()

    def init_core(self) -> None:
        """Loads the LLM instance and system prompts."""
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        system_prompt = PromptLoader.load_system_prompt(self.config, system_file)

        model_config_name = self.config.get(ProgramSetting.MODEL_CONFIG_NAME)
        self.models.load(model_config_name, system_prompt)

    def load_module(self, name: str):
        """Exposed API to turn on hardware features at runtime."""
        return self.modules.load_module(name)

    def unload_module(self, name: str):
        """Exposed API to free up VRAM/resources at runtime."""
        self.modules.unload_module(name)

    def _handle_tool_call(self, tool_call_string: str):
        """Processes tool XML blocks and re-triggers the chat loop."""
        self.history.add_message(ChatRoles.ASSISTANT, tool_call_string)
        tool_result = f"<result>\nTool execution confirmed.\n</result>"
        self.history.add_message(ChatRoles.TOOL, tool_result)
        self.history.save()
        # Re-trigger to let LLM process the tool result
        self.start_chat(user_input=None)

    def start_chat(self, user_input: Optional[str]):
        """Executes one interaction turn with the LLM and enabled modules."""
        if not self.llm:
            return

        try:
            # 1. Update History with User Input (The Memory Fix)
            if user_input and user_input.strip():
                self.history.add_message(ChatRoles.USER, user_input)

            # 2. Setup Streaming Orchestrator
            ui_tools = self.ui.get_components()
            
            # SAFE: Inside try block to prevent silent crashes
            voice_mod = self.modules['voice'] 
            
            orchestrator = StreamOrchestrator(
                voice_module=voice_mod,
                output_printer=ui_tools["printer"],
                handler_manager=ui_tools["handler"],
                token_processor=ui_tools["formatter"],
                assistant_prompt=self.chat.assistant_prompt
            )

            # 3. Request LLM Stream
            stream = self.llm.chat(
                self.chat.messages,
                stream=True,
                options=self.model_params
            )

            # 4. Process the stream
            result = orchestrator.run(stream)

            if result.tool_call_detected:
                self._handle_tool_call(result.tool_buffer)
            else:
                if result.accumulated_text:
                    self.history.add_message(ChatRoles.ASSISTANT, result.accumulated_text)

        except Exception as e:
            func.log(f"Program: Chat Error: {e}", level="CRITICAL")
            func.log(traceback.format_exc(), level="ERROR")

        finally:
            # 5. Cleanup Turn
            self.ui.reset_turn()
            
            # Wait for sound card to drain if voice is active
            voice = self.modules['voice']
            if voice:
                voice.collect_audio() 
            
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
            llm_stream_finished_callback=lambda: None
        )

        try:
            self.chat.loop()
        except KeyboardInterrupt:
            func.log("\nProgram: Shutdown initiated.")
        finally:
            self.modules.shutdown()