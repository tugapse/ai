import os
import traceback
import gc
import json
from typing import Optional, Any, Dict

# Core logic and message types
from chat.chat import Chat, ChatRoles
from core.llms.base_llm import BaseModel
from config import ProgramConfig, ProgramSetting
from color import Color

# Agent & Tools
from agents.agent import Agent
from modules.memory.vector_memory_module import VectorMemoryModule
from modules.memory.vector_memory import VectorMemory
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

    def __init__(self) -> None:
        self.chat = Chat()
        # Preserving all state variables
        self.clear_on_init = False
        self.write_to_file = False
        self.output_filename = None
        self.active_executor = None
        self.agent = None
        self.llm_initialized = False
        self.tool_registry = ToolRegistry()
        self.vector_memory : Optional[VectorMemory] = None
        self.allow_tools = False
        self._active_tools_system_prompt = ""


    @property
    def llm(self) -> Optional[BaseModel]:
        """Standard lazy-loader for the local LLM."""
        self._ensure_llm_loaded()
        return self.models.llm if self.models else None

    @llm.setter
    def llm(self, value):
        if self.models:
            self.models.llm = value
            self.llm_initialized = True

    @property
    def model_params(self) -> dict:
        self._ensure_llm_loaded()
        return self.models.get_params() if self.models else {}

    # --- INITIALIZATION LOGIC ---

    def load_config(self, args=None):
        self.config: ProgramConfig = ProgramConfig.load(args=args)
        self.models : ModelOrchestrator= ModelOrchestrator(self.config)
        self.history : HistoryManager = HistoryManager(self.chat)
        self.modules : ModuleRegistry = ModuleRegistry(self.config)
        self.ui  = UIOrchestrator(self.config)

    def init_config(self, args):
        """Processes CLI arguments and enables modules."""
        CliConfig.apply_cli_args_to_config(self.config, args)

        if hasattr(args, "modules") and args.modules:
            for mod_name in args.modules:
                self.config.set(f"{mod_name.upper()}_ENABLED", True)
                func.log(f"Config: Enabled module '{mod_name}' via CLI argument.", level="DEBUG")
        
        if self.modules:
            self.modules.load_all()

    def init_program(self) -> None:
        """Initializes session paths, UI, and the dynamic tool registry."""
        session_paths = SessionManager.initialize_session_paths(self.config)
        self.history.initialize_session(session_paths)
        self.ui.initialize(self.history.get_log_path())
        
        self.load_tool_registry()
        func.log("Program initialized with configuration and modules.")

    def load_tool_registry(self):
        """Orchestrates system, module, and user tool loading."""
        func.log("Loading System tools into Jarvis system")
        for name, tool_ref in AVAILABLE_TOOLS.items():
            self.tool_registry.register_tool(name, tool_ref)
        

        func.log("Loading User tools into Jarvis system")
        user_tools_dir = os.path.join(func.get_root_directory(), "tools")
        load_and_register_user_tools(self.tool_registry, user_tools_dir)
        self._load_vector_memory()
        
        if self.models:
            self._active_tools_system_prompt = BaseModel.format_tools_for_prompt(self.tool_registry)
            func.log(f"Program: Dynamic tool protocol injected into System Prompt. {self._active_tools_system_prompt}", level="DEBUG")
    
    def _load_vector_memory(self):
        if self.modules and (vector_memory := self.modules['vector_memory']):
            vector_memory.initialize("chat_db", self.llm)
            self.vector_memory = vector_memory.get_instance()
            tools = self.vector_memory.tools.get_tools() if self.vector_memory else {}
            for name, tool_ref in tools.items(): 
                self.tool_registry.register_tool(name, tool_ref)

    # --- CHAT & AGENTIC LOOP ---

    def start_chat(self, user_input: Optional[str]):
        """Executes interaction turns with the LLM using an Autonomous Agent Loop."""
        if not self.llm: return

        try:
            if user_input and user_input.strip():
                self.history.add_message(ChatRoles.USER, user_input)

            orchestrator = self._setup_orchestrator()
            options = self.model_params.copy() if self.model_params else {}
            
            self._run_agent_loop(orchestrator, options)

        except Exception as e:
            func.log(f"Program: Chat Error: {e}", level="CRITICAL")
            func.log(traceback.format_exc(), level="ERROR")
            if self.llm: self.llm.request_shutdown()
        finally:
            self._cleanup_after_turn()

    def _run_agent_loop(self, orchestrator: StreamOrchestrator, options: dict):
        """Handles the continuous 'Thought-Action' cycle until completion."""
        step_count = 0
        MAX_STEPS_BEFORE_WARNING = 5
        
        if not self.llm: 
            raise ValueError("LLM not initialized")

        while True:
            step_count += 1
            if step_count > MAX_STEPS_BEFORE_WARNING:
                self._inject_sentinel_warning(step_count)

            # --- INFERENCE ---
            stream = self.llm.chat(self.chat.messages, stream=True, options=options)
            stream_result = orchestrator.run(stream)

            if stream_result.interrupted:
                func.log("\nProgram: LLM stream interrupted by user. Signaling stop.", level="INFO")
                if self.llm: self.llm.request_shutdown()
                self.chat.current_message = "[Generation interrupted by user]"
                break

            # --- ACTION (Tool Handshake) ---
            if stream_result.tool_calls:
                for tool_call in stream_result.tool_calls:
                    self._process_tool_call(tool_call)
                continue # Loop back for next response based on tool results

            # --- COMPLETION ---
            if stream_result.accumulated_text:
                self.history.add_message(ChatRoles.ASSISTANT, stream_result.accumulated_text)
                self.chat.current_message = stream_result.accumulated_text
                if self.vector_memory: 
                    func.log("Addind memory to chat", level="DEBUG")
                    self.vector_memory.add_memory(self.chat.current_message,source="SELF_TURN", memory_type="chat_turn")
            break

    def _process_tool_call(self, tool_call: dict):
        """Handles the execution of a single tool, including HIL permissions."""
        name = tool_call["name"]
        args = tool_call["args"]
        
        func.log(f"\n[ORCHESTRATOR]: Action Requested -> {name}", level="INFO")
        func.log(f"\n -> {args}", level="INFO")
        func.out(f"\nUsing tool: {name} Args: {args}")
        
        # Human-In-The-Loop (HIL) Gatekeeper
        if name in getattr(self.llm, "HIL_TOOLS", []):
            if not self._request_human_permission(name, args):
                result_data = {
                    "status": "DENIED", 
                    "error": "User denied execution."
                }
                func.log("[ORCHESTRATOR]: Execution blocked by user.", level="WARNING")
            else:
                result_data = self.tool_registry.execute_tool(name, args)
        else:
            result_data = self.tool_registry.execute_tool(name, args)
        
        self._record_interaction(name, args, result_data)

    # --- PRIVATE HELPERS ---

    def _request_human_permission(self, name: str, args: dict) -> bool:
        func.out(f"\n{Color.YELLOW}[J.A.R.V.I.S. REQUESTS PERMISSION]{Color.RESET}")
        func.out(f"Action: {name}\nArgs: {json.dumps(args, indent=2)}")
        confirm = input(f"{Color.CYAN}Proceed? (y/n): {Color.RESET}").lower()
        return confirm == 'y'

    def _record_interaction(self, name: str, args: dict, result_data: dict):
        func.log(f"[ORCHESTRATOR]: Tool result: {result_data.get('status')}", level="DEBUG")
        self.chat.messages.append({
            "role": "assistant",
            "content": "", 
            "tool_calls": [{"function": {"name": name, "arguments": args}}]
        })
        self.chat.messages.append({
            "role": "tool", "name": name, "content": json.dumps(result_data) 
        })

    def _inject_sentinel_warning(self, step_count: int):
        warning_msg = (
            f"SYSTEM WARNING: Autonomous loop has reached {step_count} steps. "
            "If you haven't found a solution, summarize your progress and ask the user for guidance."
        )
        self.chat.messages.append({"role": "system", "content": warning_msg})
        func.log(f"[SENTINEL]: Step limit exceeded. Warning injected.", level="WARNING")

    def _setup_orchestrator(self) -> StreamOrchestrator:
        ui_tools = self.ui.get_components()
        voice_mod = self.modules["voice"] if self.modules else None
        return StreamOrchestrator(
            voice_module=voice_mod,
            output_printer=ui_tools["printer"],
            handler_manager=ui_tools["handler"],
            token_processor=ui_tools["formatter"],
            debug_voice=False,
        )

    def _cleanup_after_turn(self):
        self.ui.reset_turn()
        try:
            if self.modules and (voice := self.modules["voice"]):
                voice.collect_audio()
        except: pass
        self.history.save()
        self.chat.chat_finished()
        func.out("")

    # --- CORE UTILITIES ---

    def _ensure_llm_loaded(self) -> None:
        if not self.allow_tools: self._active_tools_system_prompt = ""
        system_file = self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
        system_prompt = PromptLoader.load_system_prompt(self.config, system_file) + self._active_tools_system_prompt
        
        if not self.llm_initialized:
            func.log("Program: Lazily loading LLM...", level="DEBUG")
            if self.models is None:
                self.models = ModelOrchestrator(self.config)

            self.models.load(
                self.config.get(ProgramSetting.MODEL_CONFIG_NAME), system_prompt,
                self.tool_registry
            )
            self.llm_initialized = True
            # print(system_prompt)
            # exit()
            func.log("Program: LLM loaded.", level="DEBUG")
        elif self.models and self.models.llm:
            self.models.llm.system_prompt = system_prompt



    def _handle_agent_run_requested(self, prompt: str) -> None:
        if not self.agent:
            self.agent = Agent(self)
        if self.agent:
            try:
                self.agent.run(user_prompt=prompt)
            except Exception as e:
                func.log(f"Agent execution failed: {e}", level="ERROR")
                func.log(traceback.format_exc(), level="ERROR")

    def run(self) -> None:
        self.allow_tools = True
        func.log("Program: Interface active.")
        if not self.llm:
            raise RuntimeError("LLM failed to initialize. Cannot start chat loop.")
        
        EventBinder.bind_core_events(
            chat=self.chat,
            llm=self.llm,
            start_chat_callback=self.start_chat,
            output_requested_callback=lambda: (
                self.active_executor.output_requested() if self.active_executor else None
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