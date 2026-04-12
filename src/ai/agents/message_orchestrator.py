import os
import copy
import json
from typing import Dict, Any, Optional

import functions as func
from color import Color
from terminal_ui import TerminalUI  # Importing your new shared UI class
from .specialist_manager import SpecialistManager
from .memory_manager import MemoryManager

MAX_ITERATIONS = 100
MANAGER_AGENT_ROLE = "management"

class MessageOrchestrator:
    """
    Orchestrates the execution, message routing, and state management 
    of a multi-agent system based on a defined pipeline configuration.
    """

    def __init__(self, connector: Any, registry: Any, pipeline_config: Dict[str, Any], module_registry: Any):
        """
        Initializes the MessageOrchestrator.

        Args:
            connector (Any): The LLM connector used to send requests to the models.
            registry (Any): The registry containing available tools for the agents.
            pipeline_config (Dict[str, Any]): The configuration defining the agents and pipeline.
            module_registry (Any): The application's module registry.
        """
        self.connector = connector
        self.registry = registry
        self.pipeline_config = pipeline_config
        self.agents = pipeline_config.get("agents", {})
        self.history = []
        self.auto_authorized_tools = set()
        self.format_error_count = 0  # Tracks consecutive JSON format failures
        
        specialist_config = {
            "write_file": "You are a Senior Software Engineer. Generate the full, raw content for the file. No JSON, no preamble.",
            "patch_file": "You are a Senior Developer. Generate only the specific code block to be inserted. Raw text only.",
            "generate_doc": "You are a Senior Technical Writer. Create exhaustive, deep-dive documentation in Markdown."
        }
        self.specialist_manager = SpecialistManager(self.connector, specialist_config)

        self.memory = MemoryManager(list(self.agents.keys()))
        self.module_registry = module_registry
        self.vector_memory = None

    def run_loop(self, user_prompt: str, session_id: str):
        """
        Executes the main orchestration loop, routing tasks between agents 
        and tools until a stopping condition or max iterations are reached.

        Args:
            user_prompt (str): The initial objective or prompt from the user.
            session_id (str): The unique ID for the current agent session.
        """
        # Initialize vector memory if the module is enabled
        vector_memory_module = self.module_registry["vector_memory"]
        if vector_memory_module:
            vector_memory_module.initialize(session_id=session_id, connector=self.connector)
            self.vector_memory = vector_memory_module.get_instance()

        if self.vector_memory:
            func.log("VectorMemory is enabled for this session.")
        else:
            func.log("VectorMemory is disabled (module not loaded).")

        TerminalUI.header("Pipeline Execution Start", "Agent Orchestrator")
        
        current_agent = self.pipeline_config.get("entry_point", "MASTER")
        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        
        self.memory.add_message_to_agent(current_agent, {
            "from": "USER",
            "message": user_prompt,
            "task": user_prompt
        })
        
        # if self.vector_memory:
        #     self.vector_memory.add_memory(content=user_prompt, source="USER", memory_type="objective")
        
        for i in range(max_iterations):
            # initialization
            memory = self.memory.get_agent_memory(current_agent)
            msgs = memory.messages_received
            
            for msg in reversed(msgs):
                if msg.get("from") != "SYSTEM":
                    memory.current_task = msg.get("task") or msg.get("message")
                    break
            
            # Use the manifest's priority or fallback
            display_task = memory.manifest.get("current_priority", "Analyzing objectives..." if i == 0 else memory.current_task)
            
         

            # Deep copy to prevent accidental global registry modifications
            agent_config = copy.deepcopy(self.agents.get(current_agent, {}))
            if not agent_config:
                func.error(f"\n[!] Agent {current_agent} not defined.")
                break
                
            tool_docs = [self.registry.get_tool_info(t) for t in agent_config.get("tools", [])]
            agent_config["tool_descriptions"] = "\n".join(tool_docs)

            payload = self._prepare_payload(user_prompt, current_agent)
            
            # Update the status (overwriting the thinking animation)
            TerminalUI.status(current_agent, display_task)
            
            response = self.connector.send_request(
                payload, 
                agent_config["prompt_file_path"],
                agent_config=agent_config
            )
            
            if response.get("status") == "FAILED":
                self.format_error_count += 1
                if self.format_error_count >= 3:
                    # TerminalUI.clear_line()
                    TerminalUI.auth_request("{Color.RED}⛔ Agent {current_agent} is stuck in a format loop.","")
                    if input(f"Quit the pipeline? (y/n/all): ").lower().strip() in ['y', 'yes']:
                        break

                TerminalUI.clear_line()
                func.out(f"\n{Color.RED}⚠ Format Error in {current_agent} (Strike {self.format_error_count}){Color.RESET}")
                error_msg = response.get("error", "Unknown error")
                self.memory.add_message_to_agent(current_agent, {
                    "from": "SYSTEM",
                    "message": f"CRITICAL: Invalid XML format. Error: {error_msg}. You must output ONLY valid XML."
                })
                continue
            else:
                self.format_error_count = 0  # Reset strike counter on successful parse

            next_agent = self._process_agent_response(response, current_agent, agent_config)
            
            if next_agent is None or next_agent == "STOP": 
                # TODO in the future use this as a loop stop and not an app stop
                TerminalUI.log_step("Pipeline reached STOP state.", "SUCCESS")
                break
                
            current_agent = next_agent

    def _prepare_payload(self, user_prompt: str, current_agent: str) -> Dict[str, Any]:
        """
        Constructs the state payload containing history, context, and objectives 
        to be sent to the current agent.

        Args:
            user_prompt (str): The overall user objective.
            current_agent (str): The name of the agent being prompted.

        Returns:
            Dict[str, Any]: The payload dictionary ready for the LLM connector.
        """
        known_files = [
            res["parameters"].get("path") 
            for res in self.memory.context.tool_results 
            if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"
        ]

        memory = self.memory.get_agent_memory(current_agent)
        agent_config = self.agents.get(current_agent, {})
        is_management = agent_config.get("role") == MANAGER_AGENT_ROLE
        latest_task = memory.messages_received[-1].get("message", "Continue task.") if memory.messages_received else "No specific task."
        payload = {
            "objective": user_prompt if is_management else latest_task,
            "agent_notes": memory.notes,
            "messages_received": memory.messages_received,
            "conversation_history": memory.history[-10:],
            "plan": self.memory.context.plan,
            "current_step": self.memory.context.current_step_index,
            "recent_outcomes": self._format_recent_outcomes(self.memory.context.tool_results[-3:]),
            "context": {"files_in_project": list(set(filter(None, known_files)))}
        }
        
        if self.vector_memory and len(memory.messages_received) % 4 == 0: 
            relevant_memories = self.vector_memory.retrieve_memories(query=latest_task, top_k=7)
            # Join memories into a string for the prompt context
            payload["long_term_memory"] = "\n- ".join(relevant_memories)

        if self.memory.context.repeat_count >= 3:
            payload["SYSTEM_ADVISORY"] = "WARNING: You are repeating the exact same tool calls. Change your strategy immediately to avoid an infinite loop."
            
        return payload

    def _format_recent_outcomes(self, outcomes: list) -> list:
        """
        Truncates massive tool outputs to protect the LLM context window.
        
        Args:
            outcomes (list): A list of recent tool execution outcomes.
            
        Returns:
            list: The formatted and safely truncated list of outcomes.
        """
        formatted = []
        for o in outcomes:
            res_str = json.dumps(o["result"])
            if len(res_str) > 1500:
                res_str = res_str[:1500] + "... [TRUNCATED FOR LENGTH]"
            formatted.append({
                "tool": o["tool"],
                "result": res_str
            })
        return formatted

    def _process_agent_response(self, response: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> str:
        """
        Evaluates the agent's response, handling tool execution, user prompts, 
        and determining the next agent to transition to.

        Args:
            response (Dict[str, Any]): The parsed response from the agent.
            current_agent (str): The name of the currently active agent.
            agent_config (Dict[str, Any]): The configuration for the current agent.

        Returns:
            str: The name of the next agent to transition to, or "STOP".
        """
        action = response.get("action", {})
        tool_name = action.get("tool_name")
        params = action.get("tool_parameters", {})
        agent_target = str(action.get("agent_target", "")).strip().upper()
        
        if msg_to_user := response.get("response_to_user"):
            TerminalUI.message(current_agent, msg_to_user)
            if self.vector_memory:
                self.vector_memory.add_memory(content=msg_to_user, source=current_agent, memory_type="communication")

        if self.vector_memory:
            if thought := response.get("thought"):
                self.vector_memory.add_memory(content=thought, source=current_agent, memory_type="thought")
        self.memory.update_agent_history_and_notes(current_agent, response)
        
        self.memory.check_stagnation(tool_name, params)
        
        if agent_target == "USER":
            question = action.get("message_to_target") or "The agent needs clarification."
            TerminalUI.message(current_agent, question, Color.NORMAL_CYAN)
            user_reply = input(f"{Color.BLUE}❯ {Color.RESET}").strip()
            self.memory.add_message_to_agent(current_agent, {"from": "USER", "message": user_reply, "task": user_reply})
            return current_agent

        is_tool_empty = not tool_name or str(tool_name).strip().upper() == "NULL"
        target = self._validate_target(agent_target, is_tool_empty, current_agent, agent_config)

        if target == "STOP": return "STOP"

        if not is_tool_empty:
            if not self._handle_tool_execution(tool_name, params, current_agent, agent_config):
                return current_agent 

        msg = action.get("message_to_target")
        task = action.get("task_for_target", "")
        if msg and target != "STOP" and target != current_agent:
            self.memory.add_message_to_agent(target, {"from": current_agent, "message": msg, "task": task})

        return target if target and target != "NULL" else current_agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> bool:
        """
        Authorizes and executes a specific tool requested by the agent. 
        Routes to a specialist worker for high-complexity tools.

        Args:
            tool_name (str): The name of the tool to execute.
            params (Dict[str, Any]): The parameters for the tool.
            current_agent (str): The name of the requesting agent.
            agent_config (Dict[str, Any]): The configuration for the requesting agent.

        Returns:
            bool: True if the tool executed successfully, False otherwise.
        """
        if tool_name not in agent_config.get("tools", []):
            self.memory.add_message_to_agent(current_agent, {"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            return False

        # Specialist Interceptor
        if self.specialist_manager.is_specialist_tool(tool_name):
            TerminalUI.clear_line()
            func.out(f"{Color.NORMAL_CYAN}◈ Launching Specialist for {tool_name}...{Color.RESET}")
            
            refined_content = self.specialist_manager.invoke(tool_name, params)
            
            # Map the specialist output to the correct tool parameter
            if tool_name == "patch_file":
                params["replace"] = refined_content
            else:
                params["content"] = refined_content

        # Authorization Gates
        if not self._gatekeeper(tool_name, params):
            self.memory.add_message_to_agent(current_agent, {"from": "USER", "message": f"DENIED: {tool_name} was blocked."})
            return False

        result = self.registry.execute_tool(tool_name, params)
        # if self.vector_memory:
        #     self.vector_memory.add_memory(
        #         content=f"Tool '{tool_name}' was called and returned: {json.dumps(result)}",
        #         source="TOOL",
        #         memory_type="observation"
        #     )
        self.memory.record_tool_result(current_agent, tool_name, params, result)
        return True

    def _gatekeeper(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """
        Checks if a tool requires manual user authorization and prompts the user if needed.

        Args:
            tool_name (str): The name of the tool being requested.
            params (Dict[str, Any]): The parameters supplied for the tool.

        Returns:
            bool: True if authorized (or auto-authorized), False if denied.
        """
        if tool_name in self.auto_authorized_tools or tool_name not in ["execute_command", "patch_file", "write_file"]:
            return True
            
        target = params.get('path') or params.get('command') or "System"
        TerminalUI.auth_request(tool_name, target, params.get('command', ""))

        # # Send a desktop notification to grab user's attention for authorization
        # self.registry.execute_tool("send_notification", {
        #     "title": "Authorization Required",
        #     "message": f"Agent wants to run '{tool_name}'. Please check your terminal to approve or deny.",
        #     "urgency": "critical"
        # })
        
        choice = input(f"Allow? (y/n/all): ").lower().strip()
        if choice == 'all':
            self.auto_authorized_tools.add(tool_name)
            return True
        return choice in ['y', 'yes']

    def _validate_target(self, target_raw: str, is_tool_empty: bool, current_agent: str, agent_config: Dict[str, Any]) -> str:
        """
        Validates the agent's intended transition target against its allowed targets.

        Args:
            target_raw (str): The raw target string provided by the agent.
            is_tool_empty (bool): Whether the agent refrained from calling a tool.
            current_agent (str): The name of the active agent.
            agent_config (Dict[str, Any]): The configuration of the active agent.

        Returns:
            str: The validated target, or the current agent if validation fails.
        """
        if target_raw == "USER": return "USER"
        allowed_targets = agent_config.get("allowed_targets", ["STOP", "USER"])
        if target_raw and target_raw not in allowed_targets:
            self.memory.add_message_to_agent(current_agent, {"from": "SYSTEM", "message": f"Invalid transition target '{target_raw}'."})
            return current_agent
        if is_tool_empty and not target_raw:
            self.memory.add_message_to_agent(current_agent, {"from": "SYSTEM", "message": "Call a tool or transition."})
            return current_agent
        return target_raw