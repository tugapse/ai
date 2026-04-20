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
        self.llm_initialized = False # NEW: Flag to track LLM initialization

   
    @property
    def llm(self):
        """Standard lazy-loader for the local LLM."""
        self._ensure_llm_loaded()
        return self.models.llm

    @llm.setter
    def llm(self, value):
        """
        NEW: Allows us to inject a Remote Link or a specific LLM instance.
        This is what the Client Mode uses to 'become' the remote brain.
        """
        if self.models:
            self.models.llm = value
            self.llm_initialized = True
            # func.log("Program: LLM instance injected via setter.", level="DEBUG")

    @property
    def model_params(self) -> dict:
        # Ensure LLM is loaded only when model parameters are accessed
        self._ensure_llm_loaded()
        return self.models.get_params()

    def load_config(self, args=None):
        self.config = ProgramConfig.load(args=args)
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

        self.modules.load_all()

    def _ensure_llm_loaded(self) -> None:
        """
        Ensures the LLM is loaded and initialized only if it hasn't been already.
        This method should be called before any operation requiring the LLM.
        """
        if not self.llm_initialized:
            func.log("Program: Lazily loading LLM...", level="DEBUG")
            if self.models is None:
                self.models = ModelOrchestrator(self.config)

            system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
            system_prompt = PromptLoader.load_system_prompt(self.config, system_file)
            self.models.load(self.config.get(ProgramSetting.MODEL_CONFIG_NAME), system_prompt)
            self.llm_initialized = True
            func.log("Program: LLM loaded.", level="DEBUG")


    def _handle_tool_call(self, tool_call_string: str):
        # This method implicitly needs LLM for start_chat, so _ensure_llm_loaded
        # will be called by start_chat's access to self.llm or self.model_params.
        self.history.add_message(ChatRoles.ASSISTANT, tool_call_string)
        tool_result = f"<result>\\nTool execution confirmed.\\n</result>"
        self.history.add_message(ChatRoles.TOOL, tool_result)
        self.history.save()
        self.start_chat(user_input=None)

    def start_chat(self, user_input: Optional[str]):
        """Executes one interaction turn with the LLM and enabled modules."""
        # LLM access here will trigger _ensure_llm_loaded
        if not self.llm: # Accessing self.llm here triggers the lazy load
            return

        stream_result = None # Initialize to None

        try:
            if user_input and user_input.strip():
                self.history.add_message(ChatRoles.USER, user_input)

            ui_tools = self.ui.get_components()

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
                debug_voice=False
            )

            stream = self.llm.chat( # Accessing self.llm here triggers the lazy load
                self.chat.messages,
                stream=True,
                options=self.model_params # Accessing self.model_params here triggers the lazy load
            )

            stream_result = orchestrator.run(stream) # Capture the result here

            # Check if the stream was interrupted by KeyboardInterrupt
            if stream_result.interrupted:
                func.log("\nProgram: LLM stream interrupted by user (Ctrl+C). Signaling LLM to stop.", level="INFO")
                self.llm.request_shutdown() 
                self.chat.current_message = "[Generation interrupted by user]"
            elif stream_result.accumulated_text:
                self.history.add_message(ChatRoles.ASSISTANT, stream_result.accumulated_text)
                self.chat.current_message = stream_result.accumulated_text # Ensure current_message is set for history

        except Exception as e:
            func.log(f"Program: Chat Error: {e}", level="CRITICAL")
            func.log(traceback.format_exc(), level="ERROR")
            if self.llm:
                self.llm.request_shutdown()

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

        # EventBinder.bind_core_events takes self.llm as an argument.
        # This access will trigger _ensure_llm_loaded before binding,
        # which is appropriate as the event binder needs the LLM.
        EventBinder.bind_core_events(
            chat=self.chat,
            llm=self.llm, # Accessing self.llm here triggers the lazy load
            start_chat_callback=self.start_chat,
            output_requested_callback=lambda: self.active_executor.output_requested() if self.active_executor else None,
            llm_stream_finished_callback=lambda _: None # This callback is not strictly needed for shutdown, as start_chat handles it.
        )

        try:
            self.chat.loop()
        except KeyboardInterrupt:
            func.log("\nProgram: Shutdown initiated (KeyboardInterrupt caught in chat.loop).")
        finally:
            if self.modules: self.modules.shutdown()
            self.shutdown()

    def shutdown(self) -> None:
        """
        Safety-first shutdown. Prevents crashes if exiting during boot.
        """
        # If config was never loaded, we can't do anything else.
        if not hasattr(self, 'config') or self.config is None:
            return

        # Only try to kill the LLM if it was actually initialized
        if self.llm_initialized and self.models:
            try:
                # Direct access to avoid triggering the lazy-load @property
                llm_instance = self.models.llm
                if llm_instance:
                    llm_instance.request_shutdown()
            except:
                pass
        
        func.log("JARVIS Shutdown complete.", level="DEBUG")

    def route_session(self, filepath: str) -> None:
        """
        Allows external modules (like the API Server) to instruct JARVIS
        to look at a specific memory file before processing a request.
        """
        if self.history:
            self.history.switch_active_session(filepath)