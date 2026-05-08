import os
import traceback
import gc
import json
from typing import Optional, Any

# Core logic and message types
from chat.chat import Chat, ChatRoles
from core.llms.base_llm import BaseModel
from config import ProgramConfig, ProgramSetting
from color import Color

# Agent
from agents.agent import Agent
from tools.tool_registry import ToolRegistry
from tools.agent_tools import AVAILABLE_TOOLS
from tools.tool_loader import load_and_register_user_tools

# Services Orchestration
from services.session_manager import SessionManager
from services.prompt_loader import PromptLoader
from services.config_helper import CliConfig
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

    config: ProgramConfig
    models: Optional[ModelOrchestrator]
    history: Optional[HistoryManager]
    modules: Optional[ModuleRegistry]
    ui: UIOrchestrator
    agent: Optional[Agent]

    def __init__(self) -> None:
        self.chat = Chat()
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self.active_executor = None
        self.agent = None
        self.modules = None
        self.history = None
        self.models = None
        self.llm_initialized = False
        self.tool_registry = ToolRegistry()

    @property
    def llm(self) -> Optional[BaseModel]:
        """Standard lazy-loader for the local LLM."""
        self._ensure_llm_loaded()
        return self.models.llm 

    @llm.setter
    def llm(self, value):
        if self.models:
            self.models.llm = value
            self.llm_initialized = True

    @property
    def model_params(self) -> dict:
        self._ensure_llm_loaded()
        return self.models.get_params()

    def load_config(self, args=None):
        self.config = ProgramConfig.load(args=args)
        self.models = ModelOrchestrator(self.config)
        self.history = HistoryManager(self.chat)
        self.modules = ModuleRegistry(self.config)
        self.ui = UIOrchestrator(self.config)

    def init_config(self, args):
        CliConfig.apply_cli_args_to_config(self.config, args)

        if hasattr(args, "modules") and args.modules:
            for mod_name in args.modules:
                self.config.set(f"{mod_name.upper()}_ENABLED", True)
                func.log(
                    f"Config: Enabled module '{mod_name}' via CLI argument.",
                    level="DEBUG",
                )
        self.modules.load_all()

    def init_program(self) -> None:
        session_paths = SessionManager.initialize_session_paths(self.config)
        self.history.initialize_session(session_paths)
        self.ui.initialize(self.history.get_log_path())
        self.load_tool_registry()
        func.log("Program initialized with configuration and modules.")
    
    def load_tool_registry(self):
        func.log("Loading System tools into Jarvis system")
        for name, tool_ref in AVAILABLE_TOOLS.items():
            self.tool_registry.register_tool(name, tool_ref)
        
        func.log("Loading User tools into Jarvis system")
        user_tools_dir = os.path.join(func.get_root_directory(), "tools")
        load_and_register_user_tools(self.tool_registry, user_tools_dir)

    def _ensure_llm_loaded(self) -> None:
        if not self.llm_initialized:
            func.log("Program: Lazily loading LLM...", level="DEBUG")
            if self.models is None:
                self.models = ModelOrchestrator(self.config)

            system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
            system_prompt = PromptLoader.load_system_prompt(self.config, system_file)

            self.models.load(
                self.config.get(ProgramSetting.MODEL_CONFIG_NAME), system_prompt,
                self.tool_registry
            )
            
            if self.models.llm:
                # Handshake: Inject dynamic tool schemas into the pilot's manual
                tool_rules = self.models.llm.format_tools_for_prompt()
                if tool_rules:
                    self.models.llm.system_prompt += tool_rules
                    func.log("Program: Dynamic tool protocol injected into System Prompt.", level="DEBUG")
                    
            self.llm_initialized = True
            func.log("Program: LLM loaded.", level="DEBUG")

    def _handle_agent_run_requested(self, prompt: str) -> None:
        if not self.agent:
            self.agent = Agent(self)
        
        if self.agent:
            try:
                self.agent.run(user_prompt=prompt)
            except Exception as e:
                func.log(f"Agent execution failed: {e}", level="ERROR")
                func.log(traceback.format_exc(), level="ERROR")

    def start_chat(self, user_input: Optional[str]):
        """Executes interaction turns with the LLM using an Autonomous Agent Loop."""
        if not self.llm: return

        try:
            if user_input and user_input.strip():
                self.history.add_message(ChatRoles.USER, user_input)

            ui_tools = self.ui.get_components()
            voice_mod = None
            try: voice_mod = self.modules["voice"]
            except (KeyError, TypeError): pass

            orchestrator = StreamOrchestrator(
                voice_module=voice_mod,
                output_printer=ui_tools["printer"],
                handler_manager=ui_tools["handler"],
                token_processor=ui_tools["formatter"],
                debug_voice=False,
            )

            options = self.model_params.copy() if self.model_params else {}
            
            # --- LOOP STATE ---
            step_count = 0
            MAX_STEPS_BEFORE_WARNING = 5

            # --- THE AUTONOMOUS AGENT LOOP ---
            while True:
                step_count += 1
                
                # Injection of warning if the loop is getting too long (The Stamina Meter)
                if step_count > MAX_STEPS_BEFORE_WARNING:
                    warning_msg = (
                        f"SYSTEM WARNING: Autonomous loop has reached {step_count} steps. "
                        "If you haven't found a solution, summarize your progress and ask the user for guidance."
                    )
                    # Use a system message to nudge the pilot
                    self.chat.messages.append({"role": "system", "content": warning_msg})
                    func.log(f"[SENTINEL]: Step limit exceeded. Warning injected.", level="WARNING")

                stream = self.llm.chat(  
                    self.chat.messages,
                    stream=True,
                    options=options,  
                )

                stream_result = orchestrator.run(stream)  

                if stream_result.interrupted:
                    func.log("\nProgram: LLM stream interrupted by user (Ctrl+C). Signaling LLM to stop.", level="INFO")
                    self.llm.request_shutdown()
                    self.chat.current_message = "[Generation interrupted by user]"
                    break

                # --- THE HANDSHAKE (Tool Execution) ---
                if stream_result.tool_calls:
                    for tool_call in stream_result.tool_calls:
                        if isinstance(tool_call, dict) and tool_call.get("type") == "function_call":
                            name = tool_call["name"]
                            args = tool_call["args"]
                            
                            func.log(f"\n[ORCHESTRATOR]: Action Requested -> {name}", level="INFO")
                            
                            # --- HUMAN IN THE LOOP (HIL) GATEKEEPER ---
                            if name in getattr(self.llm, "HIL_TOOLS", []):
                                func.out(f"\n{Color.YELLOW}[J.A.R.V.I.S. REQUESTS PERMISSION]{Color.RESET}")
                                func.out(f"Action: {name}\nArgs: {json.dumps(args, indent=2)}")
                                
                                confirm = input(f"{Color.CYAN}Proceed? (y/n): {Color.RESET}").lower()
                                
                                if confirm != 'y':
                                    reason = input(f"{Color.YELLOW}Reason for denial (optional): {Color.RESET}")
                                    result_data = {
                                        "status": "DENIED", 
                                        "error": f"User denied execution. Reason: {reason if reason else 'No reason provided.'}"
                                    }
                                    func.log("[ORCHESTRATOR]: Execution blocked by user.", level="WARNING")
                                else:
                                    result_data = self.tool_registry.execute_tool(name, args)
                            else:
                                # Standard autonomous execution
                                result_data = self.tool_registry.execute_tool(name, args)
                            
                            # --- RECORD INTERACTION ---
                            func.log(f"[ORCHESTRATOR]: Tool result: {result_data.get('status')}", level="DEBUG")
                            
                            # Format for LLM feedback
                            self.chat.messages.append({
                                "role": "assistant",
                                "content": "", 
                                "tool_calls": [{"function": {"name": name, "arguments": args}}]
                            })
                            
                            self.chat.messages.append({
                                "role": "tool",
                                "name": name,
                                "content": json.dumps(result_data) 
                            })
                    
                    # Loop back: J.A.R.V.I.S. will see the 'tool' message and continue
                    continue

                else:
                    # --- FINAL TEXT RESPONSE ---
                    if stream_result.accumulated_text:
                        self.history.add_message(ChatRoles.ASSISTANT, stream_result.accumulated_text)
                        self.chat.current_message = stream_result.accumulated_text
                    break

        except Exception as e:
            func.log(f"Program: Chat Error: {e}", level="CRITICAL")
            func.log(traceback.format_exc(), level="ERROR")
            if self.llm: self.llm.request_shutdown()

        finally:
            self.ui.reset_turn()
            try:
                voice = self.modules["voice"]
                if voice: voice.collect_audio()
            except: pass

            self.history.save()
            self.chat.chat_finished()
            func.out("")

    def run(self) -> None:
        func.log("Program: Interface active.")
        if not self.llm:
            raise RuntimeError("LLM failed to initialize. Cannot start chat loop.")
        
        EventBinder.bind_core_events(
            chat=self.chat,
            llm=self.llm,
            start_chat_callback=self.start_chat,
            output_requested_callback=lambda: (
                self.active_executor.output_requested()
                if self.active_executor
                else None
            ),
            llm_stream_finished_callback=lambda _: None,  
        )
        
        self.chat.add_event(Chat.EVENT_AGENT_RUN_REQUESTED, self._handle_agent_run_requested)

        try:
            self.chat.loop()
        except KeyboardInterrupt:
            func.log("\nProgram: Shutdown initiated.")
        finally:
            if self.modules: self.modules.shutdown()
            self.shutdown()

    def shutdown(self) -> None:
        func.log("Program: Initiating aggressive shutdown...", level="DEBUG")
        if not hasattr(self, "config") or self.config is None: return

        if self.llm_initialized:
            try:
                llm_instance = self.models.llm
                if llm_instance:
                    llm_instance.request_shutdown()
                    del self.models.llm
            except Exception as e:
                func.log(f"Program: Error during LLM shutdown: {e}", level="ERROR")

        if hasattr(self, "models"): del self.models
        gc.collect()
        func.log("JARVIS Shutdown complete.", level="DEBUG")

    def route_session(self, filepath: str) -> None:
        if self.history: self.history.switch_active_session(filepath)