import os
import copy
import json
from typing import Callable, Dict, Any, Optional, List

import functions as func
from color import Color
from terminal_ui import TerminalUI
from .specialist_manager import SpecialistManager
from .memory_manager import MemoryManager
from .context_sentinel import ContextSentinel

MAX_ITERATIONS = 100
MANAGER_AGENT_ROLE = "management"

class MessageOrchestrator:
    """
    Orchestrates multi-agent execution, routing, and state management.
    Integrates short-term context protection and long-term vector memory.
    """

    def __init__(self, connector: Any, registry: Any, pipeline_config: Dict[str, Any], module_registry: Any):
        """
        Initializes the orchestrator with required connectors and managers.

        Args:
            connector (Any): The LLM connector for model communication.
            registry (Any): Global registry for tool definitions.
            pipeline_config (Dict[str, Any]): Agent and pipeline definitions.
            module_registry (Any): Application-level module registry.
        """
        self.connector = connector
        self.registry = registry
        self.pipeline_config = pipeline_config
        self.agents = pipeline_config.get("agents", {})
        self.auto_authorized_tools = set()
        self.format_error_count = 0 
        
        # Managers
        specialist_cfg = {
            "write_file": "Senior Software Engineer. Raw file content generation.",
            "patch_file": "Senior Developer. Specific code block generation.",
            "generate_doc": "Technical Writer. Deep-dive documentation."
        }
        self.specialist_manager = SpecialistManager(self.connector, specialist_cfg)
        self.context_sentinel = ContextSentinel(self.connector, threshold=0.6, max_tokens=600000)

        # Memory State
        self.memory = MemoryManager(list(self.agents.keys()))
        self.module_registry = module_registry
        self.vector_memory = None

    def run_loop(self, user_prompt: str, session_id: str):
        """
        Main execution loop. Routes tasks until completion or max iterations.
        """
        self._initialize_session_modules(session_id)
        TerminalUI.header("Pipeline Execution Start", "Agent Orchestrator")
        
        current_agent = self.pipeline_config.get("entry_point", "MASTER")
        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        
        # Seed the initial objective
        self.memory.add_message_to_agent(current_agent, {
            "from": "USER", "message": user_prompt, "task": user_prompt
        })
        
        for i in range(max_iterations):
            agent_mem = self.memory.get_agent_memory(current_agent)
            
            # Extract active task from received messages
            for msg in reversed(agent_mem.messages_received):
                if msg.get("from") != "SYSTEM":
                    agent_mem.current_task = msg.get("task") or msg.get("message")
                    break
            
            TerminalUI.status(current_agent, agent_mem.manifest.get("current_priority", agent_mem.current_task))

            # Assemble Tools and Prepare Agent Config
            agent_config = copy.deepcopy(self.agents.get(current_agent, {}))
            if not agent_config:
                func.error(f"Agent {current_agent} undefined.")
                break

            active_tools = self._assemble_agent_tools(current_agent)
            agent_config["tool_descriptions"] = "\n".join([self.registry.get_tool_info(name) for name in active_tools.keys()])

            # Prepare Payload and Check Context Pressure
            payload = self._prepare_payload(user_prompt, current_agent)
            payload, was_compressed = self.context_sentinel.enforce_limits(
                current_agent, self.memory, payload, vector_memory=self.vector_memory
            )
            
            if was_compressed:
                TerminalUI.log_step(f"Sentinel: Context distilled & archived for {current_agent}", "INFO")

            # Request LLM Response
            response = self.connector.send_request(payload, agent_config["prompt_file_path"], agent_config=agent_config)
            
            if response.get("status") == "FAILED":
                if not self._handle_format_error(current_agent, response.get("error")):
                    break
                continue
            
            self.format_error_count = 0 

            # Process outcome and transition
            next_agent = self._process_agent_response(response, current_agent, agent_config)
            
            if next_agent == "DONE":
                func.log(f"Cycle complete for {current_agent}. Clearing memory.", level="WARN")
                self.memory.clear(current_agent)
                next_agent = "MASTER"
            
            if next_agent in [None, "STOP"]: 
                TerminalUI.log_step("Pipeline execution finished.", "SUCCESS")
                break
                
            current_agent = next_agent

    def _assemble_agent_tools(self, agent_name: str) -> Dict[str, Callable]:
        """Centralized factory to build and filter the toolset for an agent."""
        allowed = self.agents.get(agent_name, {}).get("tools", [])
        tool_pool = copy.copy(self.registry.get_all_tools())

        if self.vector_memory and hasattr(self.vector_memory, 'tools'):
            tool_pool.update(self.vector_memory.tools.get_tools())

        return {n: f for n, f in tool_pool.items() if n in allowed}

    def _prepare_payload(self, user_prompt: str, agent: str) -> Dict[str, Any]:
        """Constructs the structured state payload for the LLM."""
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
        
        # Periodic long-term memory retrieval
        if self.vector_memory and len(mem.messages_received) % 4 == 0: 
            query = mem.current_task or user_prompt
            payload["long_term_memory"] = "\n- ".join(self.vector_memory.retrieve_memories(query, top_k=5))

        return payload

    def _process_agent_response(self, response: Dict[str, Any], agent: str, config: Dict[str, Any]) -> str:
        """Handles agent outputs, tool execution, and memory updates."""
        action = response.get("action", {})
        tool_name, params, target = action.get("tool_name"), action.get("tool_parameters", {}), str(action.get("agent_target", "")).strip().upper()
        
        # Sync reflections and communications to LTM
        msg = response.get("response_to_user", "")
        if thought := response.get("thought"):
            if self.vector_memory: self.vector_memory.add_memory(thought, agent, "thought")
            TerminalUI.message(agent,thought, Color.DIM)


        if msg:
            if self.vector_memory: self.vector_memory.add_memory(msg, agent, "communication")
            TerminalUI.message(agent, msg, Color.NORMAL_WHITE)

        self.memory.update_agent_history_and_notes(agent, response)
        self.memory.check_stagnation(tool_name, params)
        
        # User Interaction
        if target == "USER":
            prompt = action.get("message_to_target") or "Clarification required."
            TerminalUI.message(agent, prompt, Color.NORMAL_CYAN)
            reply = input(f"{Color.BLUE}❯ {Color.RESET}").strip()
            self.memory.add_message_to_agent(agent, {"from": "USER", "message": reply, "task": reply})
            return agent

        # Validation and execution
        is_empty = not tool_name or str(tool_name).upper() == "NULL"
        validated_target = self._validate_target(target, is_empty, agent, config)

        if not is_empty and validated_target != "STOP":
            if not self._handle_tool_execution(tool_name, params, agent, config):
                return agent 

        # Routing
        msg = action.get("message_to_target")
        if msg and validated_target not in ["STOP", agent]:
            self.memory.add_message_to_agent(validated_target, {"from": agent, "message": msg, "task": action.get("task_for_target", "")})

        return validated_target or agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], agent: str, config: Dict[str, Any]) -> bool:
        """Executes authorized tools through specialists and gatekeepers."""
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
        """Initializes and connects optional session-aware modules."""
        mod = self.module_registry["vector_memory"]
        if mod:
            mod.initialize(session_id=session_id, connector=self.connector)
            self.vector_memory = mod.get_instance()
        func.log(f"VectorMemory: {'CONNECTED' if self.vector_memory else 'DISABLED'}")

    def _format_recent_outcomes(self, outcomes: list, length=3000) -> list:
        """
        Truncates large tool outputs to protect the LLM context window.
        Safe evaluation to avoid UnboundLocalError.
        """
        formatted = []
        for o in outcomes:
            # First, convert the whole result to a string
            raw_str = json.dumps(o["result"])
            
            # Then, perform the truncation logic
            if len(raw_str) > length:
                final_res = raw_str[:length] + "... [TRUNCATED]"
            else:
                final_res = raw_str
                
            formatted.append({
                "tool": o["tool"],
                "result": final_res
            })
        return formatted

    def _handle_format_error(self, agent: str, error: str) -> bool:
        """Tracks consecutive format failures and prompts for abort."""
        self.format_error_count += 1
        if self.format_error_count >= 3:
            TerminalUI.auth_request(f"{agent} stuck in format loop.", "")
            if input("Quit? (y/N): ").lower().startswith('y'): return False
        self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"CRITICAL XML ERROR: {error}"})
        return True

    def _gatekeeper(self, tool: str, params: Dict[str, Any]) -> bool:
        """Manual authorization gate for filesystem and system operations."""
        if tool in self.auto_authorized_tools or tool not in ["execute_command", "patch_file", "write_file"]: return True
        TerminalUI.auth_request(tool, params.get('path') or params.get('command') or "System", params.get('command', ""))
        choice = input("Allow? (y/n/all): ").lower().strip()
        if choice == 'all': self.auto_authorized_tools.add(tool); return True
        return choice in ['y', 'yes']

    def _validate_target(self, target: str, is_empty: bool, agent: str, config: Dict[str, Any]) -> str:
        """Validates agent state transition logic."""
        if target == "USER": return "USER"
        allowed = config.get("allowed_targets", ["STOP", "USER"])
        if target and target not in allowed:
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"Invalid transition: {target}"})
            return agent
        if is_empty and not target:
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": "Instruction: Call a tool or transition."})
            return agent
        return target