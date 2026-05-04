import os
import copy
import json
from typing import Callable, Dict, Any, Optional, List

from config import ProgramConfig, ProgramSetting
import functions as func
from color import Color
from terminal_ui import TerminalUI
from .specialist_manager import SpecialistManager
from .memory_manager import MemoryManager
from .context_sentinel import ContextSentinel
from .session_vault import SessionVault
from core.events import Events

MAX_ITERATIONS = 100
MANAGER_AGENT_ROLE = "management"

class MessageOrchestrator(Events):
    """
    Orchestrates multi-agent execution, routing, and state management.
    Integrates short-term context protection and long-term session persistence.
    """
    EVENT_BEFORE_LLM_REQUEST = "before_llm_request"
    EVENT_AFTER_LLM_REQUEST = "after_llm_request"

    def __init__(self, connector: Any, registry: Any, pipeline_config: Dict[str, Any], module_registry: Any):
        super().__init__()
        self.connector = connector
        self.registry = registry
        self.pipeline_config = pipeline_config
        self.agents = pipeline_config.get("agents", {})
        self.auto_authorized_tools = set()
        self.format_error_count = 0

        # Specialized Managers
        self.specialist_manager = SpecialistManager(
            self.connector, 
            {"generate_doc": "Technical Writer. Deep-dive documentation."}
        )
        self.context_sentinel = ContextSentinel(
            self.connector, 
            threshold=0.9, 
            max_tokens=self.connector.get_context_limit(),
            buffer=self.connector.get_max_tokens()
        )

        # Memory State
        self.memory = MemoryManager(list(self.agents.keys()))
        self.module_registry = module_registry
        self.vector_memory = None
        
        # Session State (Initialized in run_loop)
        self.vault = None
        self.session_id = None

    def run_loop(self, user_prompt: str, session_id: str):
        """
        Main execution loop. Hydrates session if available, otherwise starts fresh.
        """
        self.session_id = session_id
        self.vault = SessionVault(session_id)
        self._initialize_session_modules(session_id)
        
        # HYDRATION PHASE
        hydrated_state = self.vault.hydrate()
        if hydrated_state:
            TerminalUI.header(f"Resuming Session: {session_id}", "Sentinel Architect")
            self._apply_state(hydrated_state)
            current_agent = hydrated_state.get("current_agent", self.pipeline_config.get("entry_point"))
            start_iteration = hydrated_state.get("iteration", 0)

            # State integrity check: If the hydrated agent isn't in the current pipeline, reset to entry point.
            if current_agent not in self.agents and current_agent not in ["STOP", "USER", "DONE"]:
                func.log(f"Stale agent '{current_agent}' in session. Resetting to entry point.", level="WARN")
                current_agent = self.pipeline_config.get("entry_point")

            func.log(f"Orchestrator: State re-inflated. Resuming as {current_agent} at iteration {start_iteration}")
        else:
            TerminalUI.header("Pipeline Execution Start", "Agent Orchestrator")
            current_agent = self.pipeline_config.get("entry_point", "MASTER")
            start_iteration = 0
            # Seed initial objective only for new sessions
            self.memory.add_message_to_agent(current_agent, {
                "from": "USER", "message": user_prompt, "task": user_prompt
            })

        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)

        for i in range(start_iteration, max_iterations):
            # Agent state validation at the start of the loop
            if current_agent in [None, "STOP"]:
                TerminalUI.log_step("Pipeline execution finished.", "SUCCESS")
                break

            agent_mem = self.memory.get_agent_memory(current_agent)
            if not agent_mem:
                # This can happen if an invalid agent is targeted.
                func.error(f"Agent '{current_agent}' not found in memory or is invalid. Stopping.")
                break

            # Context Update
            for msg in reversed(agent_mem.messages_received):
                if msg.get("from") != "SYSTEM":
                    agent_mem.current_task = msg.get("task") or msg.get("message")
                    break

            TerminalUI.status(current_agent, agent_mem.manifest.get("current_priority", agent_mem.current_task))

            # Assemble Tools and Prepare Payload
            agent_config = copy.deepcopy(self.agents.get(current_agent, {}))
            if not agent_config:
                func.error(f"Agent {current_agent} undefined.")
                break

            active_tools = self._assemble_agent_tools(current_agent)
            agent_config["tool_descriptions"] = "\n".join([self.registry.get_tool_info(name) for name in active_tools.keys()])

            payload = self._prepare_payload(user_prompt, current_agent)
            payload, was_compressed = self.context_sentinel.enforce_limits(
                current_agent, self.memory, payload, vector_memory=self.vector_memory
            )

            if was_compressed:
                TerminalUI.log_step(f"Sentinel: Context distilled for {current_agent}", "INFO")

            self.trigger("before_llm_request", {"agent": current_agent, "payload_preview": {k: v for k, v in payload.items() if k not in ['messages_received', 'conversation_history']}})
            response = self.connector.send_request(payload, agent_config["prompt_file_path"], agent_config=agent_config)
            self.trigger("after_llm_request", {"agent": current_agent, "response": response})

            if response.get("status") == "FAILED":
                if not self._handle_format_error(current_agent, response.get("error")):
                    break
                continue

            self.format_error_count = 0
            
            # Process Response and Route
            next_agent = self._process_agent_response(response, current_agent, agent_config)

            # PERSISTENCE: Commit state before moving to the next iteration
            self.vault.commit(self._capture_state(next_agent, i + 1))

            if next_agent == "DONE":
                func.log(f"Cycle complete for {current_agent}. Clearing memory.", level="WARN")
                self.memory.clear(current_agent)
                next_agent = "MASTER"

            current_agent = next_agent

    def _capture_state(self, next_agent: str, iteration: int) -> Dict[str, Any]:
        """Serializes current memory and orchestration metadata."""
        return {
            "current_agent": next_agent,
            "iteration": iteration,
            "memory": self.memory.serialize(),
            "context_plan": self.memory.context.plan,
            "step_index": self.memory.context.current_step_index,
            "auto_authorized_tools": list(self.auto_authorized_tools)
        }

    def _apply_state(self, state: Dict[str, Any]):
        """Injects serialized state back into active managers."""
        self.memory.hydrate(state.get("memory", {}))
        self.memory.context.plan = state.get("context_plan", [])
        self.memory.context.current_step_index = state.get("step_index", 0)
        self.auto_authorized_tools = set(state.get("auto_authorized_tools", []))

    def _assemble_agent_tools(self, agent_name: str) -> Dict[str, Callable]:
        allowed = self.agents.get(agent_name, {}).get("tools", [])
        tool_pool = copy.copy(self.registry.get_all_tools())
            
        return {n: f for n, f in tool_pool.items() if n in allowed}

    def _prepare_payload(self, user_prompt: str, agent: str) -> Dict[str, Any]:
        known_files = [
            res["parameters"].get("path")
            for res in self.memory.context.tool_results
            if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"
        ]
        mem = self.memory.get_agent_memory(agent)
        is_mgr = self.agents.get(agent, {}).get("role") == MANAGER_AGENT_ROLE
        
        payload = {
            "objective": user_prompt if is_mgr else (mem.messages_received[-1].get("message", "Continue.") if mem.messages_received else "Continue."),
            "agent_notes": mem.notes,
            "messages_received": mem.messages_received,
            "conversation_history": mem.history[-10:],
            "plan": self.memory.context.plan,
            "current_step": self.memory.context.current_step_index,
            "recent_outcomes": self._format_recent_outcomes(self.memory.context.tool_results[-3:]),
            "context": {"files_in_project": list(set(filter(None, known_files)))}
        }
        
        if self.vector_memory and len(mem.messages_received) % 4 == 0:
            query = mem.current_task or user_prompt
            payload["long_term_memory"] = "\n- ".join(self.vector_memory.retrieve_memories(query, top_k=5))
        return payload

    def _process_agent_response(self, response: Dict[str, Any], agent: str, config: Dict[str, Any]) -> str:
        action = response.get("action", {})
        tool_name, params = action.get("tool_name"), action.get("tool_parameters", {})
        target = str(action.get("agent_target", "")).strip().upper()

        if thought := response.get("thought"):
            if ProgramConfig.current.get(ProgramSetting.AGENT_THOUGHT, False): 
                TerminalUI.message(agent, thought, Color.DIM)

        msg = response.get("response_to_user", "")
        if msg:
            # if self.vector_memory: self.vector_memory.add_memory(msg, agent, "communication")
            TerminalUI.message(agent, msg, Color.NORMAL_WHITE)

        self.memory.update_agent_history_and_notes(agent, response)
        self.memory.check_stagnation(tool_name, params)

        if target == "USER":
            prompt = action.get("message_to_target") or "Clarification required."
            TerminalUI.message(agent, prompt, Color.NORMAL_CYAN)
            reply = input(f"{Color.BLUE}❯ {Color.RESET}").strip()
            self.memory.add_message_to_agent(agent, {"from": "USER", "message": reply, "task": reply})
            return agent

        is_empty = not tool_name or str(tool_name).upper() == "NULL"
        validated_target = self._validate_target(target, is_empty, agent, config)

        if not is_empty and validated_target != "STOP":
            if not self._handle_tool_execution(tool_name, params, agent, config):
                return agent

        msg_to_target = action.get("message_to_target")
        if msg_to_target and validated_target not in ["STOP", agent]:
            self.memory.add_message_to_agent(validated_target, {"from": agent, "message": msg_to_target, "task": action.get("task_for_target", "")})

        return validated_target or agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], agent: str, config: Dict[str, Any]) -> bool:
        if tool_name not in config.get("tools", []):
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            return False

        if self.specialist_manager.is_specialist_tool(tool_name):
            TerminalUI.clear_line()
            func.out(f"{Color.NORMAL_CYAN}◈ Specialist: {tool_name}{Color.RESET}")
            content = self.specialist_manager.invoke(tool_name, params)
            params["replace" if tool_name == "patch_file" else "content"] = content

        if not self._gatekeeper(tool_name, params):
            self.memory.add_message_to_agent(agent, {"from": "USER", "message": "Access Denied."})
            return False

        result = self.registry.execute_tool(tool_name, params)
        self.memory.record_tool_result(agent, tool_name, params, result)
        return True

    def _initialize_session_modules(self, session_id: str):
        """
        Initializes all registered modules, centralizing their tools in the ToolRegistry.
        """
        for module_name, mod in self.module_registry.items():
            if not mod:
                continue

            # Modules are pre-initialized, so we just retrieve the instance.
            instance = mod.get_instance()

            # Special handling for vector_memory to maintain direct access
            if module_name == "vector_memory":
                self.vector_memory = instance
                func.log(f"VectorMemory: {'CONNECTED' if self.vector_memory else 'DISABLED'}")

            # Register tools from the module into the central registry
            if instance and hasattr(instance, 'tools') and hasattr(instance.tools, 'get_tools'):
                module_tools = instance.tools.get_tools()
                for tool_name, tool_func in module_tools.items():
                    self.registry.register_tool(tool_name, tool_func)
                    func.log(f"Registered tool '{tool_name}' from module '{module_name}'.")

    def _format_recent_outcomes(self, outcomes: list, length=3000) -> list:
        formatted = []
        for o in outcomes:
            raw_str = json.dumps(o["result"])
            # TODO: Consider more intelligent truncation that preserves JSON structure or key info instead of naive character cut-off
            # final_res = (raw_str[:length] + "... [TRUNCATED]") if len(raw_str) > length else raw_str
            formatted.append({"tool": o["tool"], "result": raw_str})
        return formatted

    def _handle_format_error(self, agent: str, error: str) -> bool:
        self.format_error_count += 1
        
        if self.format_error_count >= 3:
            TerminalUI.header("Sentinel loop error!", f"{agent} stuck in format loop.")
            # In a non-interactive test environment, we can't ask for input.
            # We will log the error and break the loop.
            func.error(f"Agent {agent} failed to produce valid output 3 times. Halting loop.")
            return False

        error_msg = (
            f"PARSING FAILURE: {error}. "
            "Your previous output contained invalid structure. "
            "You must discard that attempt and rewrite your response. "
        )
        self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": error_msg})
        return True

    def _gatekeeper(self, tool: str, params: Dict[str, Any]) -> bool:
        if tool in self.auto_authorized_tools or tool not in ["execute_command"]: return True
        TerminalUI.auth_request(tool, params.get('path') or params.get('command') or "System", params.get('command', ""))
        choice = input("Allow? (y/n/all): ").lower().strip()
        if choice == 'all': self.auto_authorized_tools.add(tool); return True
        return choice in ['y', 'yes']

    def _validate_target(self, target: str, is_empty: bool, agent: str, config: Dict[str, Any]) -> str:
        if target == "USER": return "USER"
        allowed = config.get("allowed_targets", ["STOP", "USER"])
        if target and target not in allowed:
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"Invalid transition target: {target}"})
            return agent
        if is_empty and not target:
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": "Instruction: Call a tool or transition."})
            return agent
        return target