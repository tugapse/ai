import os
import traceback
import gc
import json
from typing import Optional, Any, Dict

# Core logic and message types
from ai.chat.chat import Chat, ChatRoles
from ai.core.llms.base_llm import BaseModel
from ai.config import ProgramConfig, ProgramSetting
from ai.color import Color
from ai.core.llms.api_retry import LLMAPIError

# Agent & Tools
from ai.agents.agent import Agent
from ai.modules.vector_memory.vector_memory_module import VectorMemoryModule
from ai.modules.vector_memory.vector_memory import VectorMemory
from ai.modules.voice.base_module import BaseVoiceModule
from ai.tools.tool_registry import ToolRegistry
from ai.tools.tool_loader import load_and_register_user_tools

# Services Orchestration
from ai.services.session_manager import SessionManager
from ai.services.prompt_loader import PromptLoader
from ai.services.config_helper import CliConfig
from ai.services.event_binder import EventBinder
from ai.services.model_orchestrator import ModelOrchestrator
from ai.services.history_manager import HistoryManager
from ai.services.module_registry import ModuleRegistry
from ai.services.ui_orchestrator import UIOrchestrator
from ai.services.stream_orchestrator import StreamOrchestrator
from ai.services.process_manager import ProcessManager

import ai.functions as func

class Program:
    """
    Main orchestrator for JARVIS.
    Coordinates services to handle LLM logic, Hardware modules,
    UI feedback, and Session persistence.
    """

    def __init__(self) -> None:
        """
        Initializes the core components of the JARVIS program, setting up
        state variables for configuration, LLM, and tool management.
        """
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
        """
        Standard lazy-loader for the local LLM. Ensures the LLM is loaded before returning it.
        :return: The initialized BaseModel instance or None.
        """
        self._ensure_llm_loaded()
        return self.models.llm if self.models else None

    @llm.setter
    def llm(self, value):
        """
        Sets the LLM instance and marks the LLM as initialized.
        :param value: The BaseModel instance to set.
        """
        if self.models:
            self.models.llm = value
            self.llm_initialized = True

    @property
    def model_params(self) -> dict:
        """
        Retrieves the current configuration parameters for the LLM.
        :return: A dictionary containing model parameters.
        """
        self._ensure_llm_loaded()
        return self.models.get_params() if self.models else {}

    # --- INITIALIZATION LOGIC ---

    def load_config(self, args=None):
        """
        Loads the primary configuration object from provided arguments or defaults.
        Initializes the ModelOrchestrator, HistoryManager, ModuleRegistry, and UIOrchestrator.
        :param args: Optional arguments object for configuration loading.
        """
        self.config: ProgramConfig = ProgramConfig.load(args=args)
        self.models : ModelOrchestrator= ModelOrchestrator(self.config)
        self.history : HistoryManager = HistoryManager(self.chat)
        self.modules : ModuleRegistry = ModuleRegistry(self.config)
        self.ui  = UIOrchestrator(self.config)

    def init_config(self, args):
        """
        Processes CLI arguments to update the configuration and loads all enabled modules.
        :param args: The arguments object containing CLI flags.
        """
        CliConfig.apply_cli_args_to_config(self.config, args)

        if hasattr(args, "modules") and args.modules:
            for mod_name in args.modules:
                self.config.set(ProgramSetting(f"{mod_name.upper()}_ENABLED"), True)
                func.log(f"Config: Enabled module '{mod_name}' via CLI argument.", level="DEBUG")
        
        if self.modules:
            self.modules.load_all()

    def init_program(self) -> None:
        """
        Performs high-level program initialization: setting up session paths,
        initializing the UI, and loading the dynamic tool registry.
        """
        session_paths = SessionManager.initialize_session_paths(self.config)
        self.history.initialize_session(session_paths)
        self.ui.initialize(self.history.get_log_path())
        
        self.load_tool_registry()
        func.log("Program initialized with configuration and modules.")

    def load_tool_registry(self):
        """
        Orchestrates the loading of tools: system-defined tools, user-defined tools,
        and memory-derived tools, registering them into the central registry.
        """
        func.log("Loading System tools into Jarvis system")
        if self.modules is not None:
            for name, tool_ref in self.modules.tool_functions().items():
                self.tool_registry.register_tool(name, tool_ref)
        

        func.log("Loading User tools into Jarvis system")
        user_tools_dir = os.path.join(func.get_root_directory(), "tools")
        load_and_register_user_tools(self.tool_registry, user_tools_dir)
        self._load_vector_memory()
        
        if self.models and self.allow_tools:
            self._active_tools_system_prompt = ToolRegistry.format_tools_for_prompt(self.tool_registry.get_all_tools())
            func.debug(f"Program: Dynamic tool protocol injected into System Prompt. {self._active_tools_system_prompt}", level="DEBUG")
    
    def _load_vector_memory(self):
        """
        Checks if the vector memory module is enabled. If so, initializes it,
        and registers any tools derived from the memory store into the tool registry.
        """
        if self.modules and (vector_memory := self.modules['vector_memory']):
            vector_memory.initialize("chat_db", self.llm)
            self.vector_memory = vector_memory.get_instance()
            tools = self.vector_memory.tools.get_tools() if self.vector_memory else {}
            for name, tool_ref in tools.items(): 
                self.tool_registry.register_tool(name, tool_ref)

    # --- CHAT & AGENTIC LOOP ---

    def start_chat(self, user_input: Optional[str]):
        """
        Executes interaction turns with the LLM using an Autonomous Agent Loop.
        Handles user input, orchestrates the streaming process, and manages the loop lifecycle.
        :param user_input: The initial text input from the user, if provided.
        """
        if not self.llm: return

        ProcessManager.set_state("activity", "responding")
        try:
            if user_input and user_input.strip():
                self.history.add_message(ChatRoles.USER, user_input)

            stream_orchestrator = self._setup_orchestrator()
            options = self.model_params.copy() if self.model_params else {}
            
            self._run_agent_loop(stream_orchestrator, options)

        except LLMAPIError as e:
            # Remote API failure (already retried): report it, keep the model and the chat alive.
            func.out(f"\n{Color.RED}[ ! ] {e.user_message()}{Color.RESET}")
        except Exception as e:
            func.log(f"Program: Chat Error: {e}", level="CRITICAL")
            func.log(traceback.format_exc(), level="ERROR")
            if self.llm: self.llm.request_shutdown()
        finally:
            self._cleanup_after_turn()
            ProcessManager.set_state("activity", "ready")

    def _run_agent_loop(self, stream_orchestrator: StreamOrchestrator, options: dict):
        """
        Handles the continuous 'Thought-Action' cycle until completion.
        This loop drives the agent's decision-making process based on LLM output.
        :param stream_orchestrator: The orchestrator responsible for handling stream output.
        :param options: The current model parameters to use during inference.
        """
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
            stream_result = stream_orchestrator.run(stream)

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
        """
        Handles the execution of a single tool requested by the LLM.
        It enforces Human-In-The-Loop (HIL) permissions if required by the LLM configuration.
        :param tool_call: A dictionary containing the tool name and arguments.
        """
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
        """
        Prompts the user via console to confirm execution of a sensitive tool.
        :param name: The name of the tool being requested.
        :param args: The arguments passed to the tool.
        :return: True if the user confirms execution, False otherwise.
        """
        func.out(f"\n{Color.YELLOW}[J.A.R.V.I.S. REQUESTS PERMISSION]{Color.RESET}")
        func.out(f"Action: {name}\nArgs: {json.dumps(args, indent=2)}")
        confirm = input(f"{Color.CYAN}Proceed? (y/n): {Color.RESET}").lower()
        return confirm == 'y'

    def _record_interaction(self, name: str, args: dict, result_data: dict):
        """
        Records the tool execution result into the chat history as a 'tool' message.
        :param name: The name of the tool executed.
        :param args: The arguments used for the tool.
        :param result_data: The structured result returned by the tool execution.
        """
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
        """
        Injects a system warning message into the chat history when the agent loop
        exceeds a predefined maximum number of steps, prompting the agent to self-correct.
        :param step_count: The current step count of the agent loop.
        """
        warning_msg = (
            f"SYSTEM WARNING: Autonomous loop has reached {step_count} steps. "
            "If you haven't found a solution, summarize your progress and ask the user for guidance."
        )
        self.chat.messages.append({"role": "system", "content": warning_msg})
        func.log(f"[SENTINEL]: Step limit exceeded. Warning injected.", level="WARNING")

    def _setup_orchestrator(self) -> StreamOrchestrator:
        """
        Sets up and returns the StreamOrchestrator instance, gathering necessary
        UI and voice components from the module registry.
        :return: A configured StreamOrchestrator object.
        """
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
        """
        Performs necessary cleanup after a single chat turn, including resetting the UI,
        collecting audio if a voice module is present, saving history, and finalizing the chat state.
        """
        self.ui.reset_turn()
        try:
            if self.modules and isinstance(voice := self.modules["voice"], BaseVoiceModule):
                    voice.collect_audio()
        except: pass
        self.history.save()
        self.chat.chat_finished()
        func.out("")

    # --- CORE UTILITIES ---

    def _ensure_llm_loaded(self) -> None:
        """
        Ensures the LLM is loaded before any operation requiring it.
        If not loaded, it dynamically loads the LLM, incorporating the system prompt
        and any active tools into the system prompt context.
        """
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

            func.log("Program: LLM loaded.", level="DEBUG")
        elif self.models and self.models.llm:
            self.models.llm.system_prompt = system_prompt


    def _handle_agent_run_requested(self, prompt: str) -> None:
        """
        Handles the event when the system requests an autonomous agent run.
        Initializes the Agent if necessary and executes its run method with the provided prompt.
        :param prompt: The prompt string triggering the agent execution.
        """
        if not self.agent:
            self.agent = Agent(self)
        if self.agent:
            try:
                self.agent.run(user_prompt=prompt)
            except Exception as e:
                func.log(f"Agent execution failed: {e}", level="ERROR")
                func.log(traceback.format_exc(), level="ERROR")

    def run(self) -> None:
        """
        Starts the main operational loop of the JARVIS program.
        Binds core events, initializes the UI, and enters the main chat loop,
        handling graceful shutdown upon interruption.
        """
        func.log("Program: Interface active.")
        self.allow_tools = True
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
            if func.ALLOW_CLEAR_CONSOLE: 
                func.clear_console()
             
            self._print_chat_header()

            
            self.chat.loop()
        except KeyboardInterrupt:
            func.log("\nProgram: Shutdown initiated.")
        finally:
            if self.modules: self.modules.shutdown()
            self.shutdown()

    def shutdown(self) -> None:
        """
        Performs a controlled and aggressive shutdown of all running services,
        ensuring the LLM connection is properly terminated and memory is released.
        """
        func.debug("Program: Initiating aggressive shutdown...", level="DEBUG")
        if not hasattr(self, "config") or self.config is None: return

        if self.llm_initialized and hasattr(self, "models") and hasattr(self.models, "llm"):
            try:
                llm_instance = self.models.llm  
                if llm_instance:
                    llm_instance.request_shutdown()
                    del self.models.llm
            except Exception as e:
                func.error(f"Program: Error during LLM shutdown: {e}")

        if hasattr(self, "models"): del self.models
        gc.collect()
        func.debug("JARVIS Shutdown complete.", level="DEBUG")

    def route_session(self, filepath: str) -> None:
        """
        Switches the active chat session to a specified file path, loading history from it.
        :param filepath: The path to the session file.
        """
        if self.history: self.history.switch_active_session(filepath)

    def _print_chat_header(self) -> None:
        """
        Prints the initial header banner to the console, displaying the active chat name
        and system status indicators.
        """
        chat_name = self.models.get_chat_name() 
    
        if func.ALLOW_CLEAR_CONSOLE:
            func.clear_console()
        
        func.out(f"{Color.CYAN} # {Color.RESET}Established neural link to: {Color.YELLOW}{chat_name}{Color.RESET}")
        func.out(f"{Color.CYAN} #{Color.PURPLE} Sentinel status: ACTIVE | Logic: INJECTED{Color.RESET}")
        func.out(f"{Color.CYAN} # {Color.RESET}-----------------------------------------------------------")