import json
from typing import Dict, Any, Optional
from .agent_tools import send_notification
import functions as func
from color import Color

MAX_ITERATIONS = 100
MANAGER_AGENT_ROLE = "management"

class MessageOrchestrator:
    def __init__(self, connector: Any, registry: Any, pipeline_config: Dict[str, Any]):
        self.connector = connector
        self.registry = registry
        self.pipeline_config = pipeline_config
        self.agents = pipeline_config.get("agents", {})
        self.history = []
        self.auto_authorized_tools = set()
        
        # --- NEW: HIGH-COMPLEXITY CONFIGURATION ---
        # These tools will trigger a "Ghost/Specialist" raw-text call
        self.high_complexity_tools = {
            "write_file": "You are a Senior Software Engineer. Generate the full, raw content for the file. No JSON, no preamble.",
            "patch_file": "You are a Senior Developer. Generate only the specific code block to be inserted. Raw text only.",
            "generate_doc": "You are a Senior Technical Writer. Create exhaustive, deep-dive documentation in Markdown."
        }

        self.context = {
            "tool_results": [], 
            "task": "",
            "plan": [], 
            "current_step_index": 1,
            "last_action_fp": None,
            "repeat_count": 0
        }
        
        self.agent_memory = {
            agent_name: {
                "notes": "System initialized.",
                "messages_received": [],
                "history": [],
                "current_task": "Waiting for tasks...",
                "manifest":{}
            }
            for agent_name in self.agents.keys()
        }

    def run_loop(self, user_prompt: str):
        func.log("Starting Pipeline Loop")
        current_agent = self.pipeline_config.get("entry_point", "MASTER")
        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        
        self.agent_memory[current_agent]["messages_received"].append({
            "from": "USER",
            "message": user_prompt,
            "task": user_prompt
        })
        
        for i in range(max_iterations):
            func.log(f"Execution loop iteration {i+1}/{max_iterations}. Agent: {current_agent}")
            
            msgs = self.agent_memory[current_agent].get("messages_received", [])
            for msg in reversed(msgs):
                if msg.get("from") != "SYSTEM":
                    self.agent_memory[current_agent]["current_task"] = msg.get("task") or msg.get("message", )
                    break
            
            display_task = self.agent_memory[current_agent].get('manifest',{}).get("current_priority", "Understanding user request")
            
            func.out(f"{Color.BLUE}[ * ] Agent {current_agent} is wortking on: {Color.RESET}{display_task}", end="", flush=True)
            func.debug("Current task: " + display_task)

            agent_config = self.agents.get(current_agent, {}).copy()
            if not agent_config:
                func.error(f"Agent {current_agent} not defined.")
                break
                
            tool_docs = [self.registry.get_tool_info(t) for t in agent_config.get("tools", [])]
            agent_config["tool_descriptions"] = "\n".join(tool_docs)

            payload = self._prepare_payload(user_prompt, current_agent)
            
            response = self.connector.send_request(
                payload, 
                agent_config["prompt_file_path"],
                agent_config=agent_config
            )
            
            if response.get("status") == "FAILED":
                func.out("\r\033[K", end="", flush=True)
                error_msg = response.get("error", "Unknown error")
                self.agent_memory[current_agent]["messages_received"].append({
                    "from": "SYSTEM",
                    "message": f"Your last output was invalid JSON. Error: {error_msg}. Fix your formatting and try again."
                })
                continue

            next_agent = self._process_agent_response(response, current_agent, agent_config)
            if next_agent is None or next_agent == "STOP": 
                func.log("Pipeline reached STOP state.")
                break
                
            current_agent = next_agent

    def _prepare_payload(self, user_prompt: str, current_agent: str) -> Dict[str, Any]:
        known_fileS_locations = [
            res["parameters"].get("path") 
            for res in self.context["tool_results"] 
            if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"
        ]

        memory = self.agent_memory.get(current_agent, {})
        agent_config = self.agents.get(current_agent, {})
        is_management = agent_config.get("role") == MANAGER_AGENT_ROLE
        latest_task = memory["messages_received"][-1].get("message", "Continue task.") if memory["messages_received"] else "No specific task."
        
        payload = {
            "objective": user_prompt if is_management else latest_task,
            "agent_notes": memory.get("notes"),
            "messages_received": memory.get("messages_received"),
            "conversation_history": memory.get("history",[])[-10:],
            "plan": self.context["plan"],
            "current_step": self.context["current_step_index"],
            "recent_outcomes": self.context["tool_results"][-3:],
            "context": {"files_in_project": list(set(filter(None, known_fileS_locations)))}
        }
        
        if self.context.get("repeat_count", 0) >= 2:
            payload["SYSTEM_ADVISORY"] = "WARNING: You are repeating tool calls. Change your strategy."
            
        return payload

    def _process_agent_response(self, response: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> str:
        action = response.get("action", {})
        tool_name = action.get("tool_name")
        params = action.get("tool_parameters", {})
        agent_target = str(action.get("agent_target", "")).strip().upper()
        
        self.agent_memory[current_agent]["manifest"] = response.get("manifest", {})
        
        self._handle_agent_outputs(response, current_agent, tool_name)
        self._update_stagnation_tracking(tool_name, params)
        
        if agent_target == "USER":
            question = action.get("message_to_target") or "The agent needs clarification."
            self.registry.execute_tool("send_notification", {"title": "Action Required", "message": f"{current_agent}: {question}."})
            user_reply = input(f"{question}\n> ").strip()
            self.agent_memory[current_agent]["messages_received"].append({"from": "USER", "message": user_reply, "task": user_reply})
            return current_agent

        is_tool_empty = not tool_name or str(tool_name).lower() == "null"
        target = self._validate_target(agent_target, is_tool_empty, current_agent, agent_config)

        if target == "STOP": return "STOP"

        if not is_tool_empty:
            # PIVOT: The tool execution now handles the specialist logic internally
            if not self._handle_tool_execution(tool_name, params, current_agent, agent_config):
                return current_agent 
                
            if not target or target == "NULL":
                return current_agent
                
        self._handle_inter_agent_messaging(action, target, current_agent)
        return target if target and target != "NULL" else current_agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> bool:
        if tool_name not in agent_config.get("tools", []):
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            return False

        # ---  THE SPECIALIST INTERCEPTOR ---
        if tool_name in self.high_complexity_tools:
            func.log(f"{Color.NORMAL_CYAN}[ SPECIALIST ] High-complexity tool '{tool_name}' detected. Launching Ghost-Writer...{Color.RESET}")
            
            # Use instructions provided by Architect, or fallback to the provided content
            goal = params.get("instructions") or params.get("content") or "Generate high-quality content based on the current objective."
            target_path = params.get("path", "unknown_file")
            
            # Trigger a CLEAN call to the LLM (No JSON!)
            refined_content = self._call_specialist_worker(
                role_description=self.high_complexity_tools[tool_name],
                path=target_path,
                goal=goal
            )
            
            # Inject the high-fidelity content back into the parameters
            params["content"] = refined_content
            func.log(f"{Color.GREEN}[ SPECIALIST ] Content generation successful.{Color.RESET}")

        # --- AUTHORIZATION GATES ---
        is_authorized = self._gatekeeper(tool_name, params)
        if not is_authorized:
            self.agent_memory[current_agent]["messages_received"].append({"from": "USER", "message": f"DENIED: {tool_name} was blocked."})
            return False

        func.log(f"[TOOL CALL]: {tool_name}")
        result = self.registry.execute_tool(tool_name, params)
        
        self.context["tool_results"].append({"agent": current_agent, "tool": tool_name, "parameters": params, "result": result})
        if result.get("status") == "SUCCESS":
            self.context["current_step_index"] += 1
        
        self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "result": result})
        return True

    def _call_specialist_worker(self, role_description: str, path: str, goal: str) -> str:
        """
        NEW: Performs a raw-text completion to bypass JSON formatting constraints.
        """
        worker_payload = {
            "task_context": f"Working on: {path}\nObjective: {goal}",
            "instruction": "Output only the raw text/code. No explanations, no JSON braces, no markdown wrapping unless it IS a markdown file."
        }
        
        # NOTE: Your connector needs a 'send_raw_request' method that returns a plain string
        raw_output = self.connector.send_raw_request(worker_payload, system_prompt=role_description)
        return raw_output.strip()

    def _gatekeeper(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """Centralized authorization gate for sensitive operations."""
        if tool_name in self.auto_authorized_tools or tool_name not in ["execute_command", "patch_file", "write_file"]:
            return True
            
        func.out(f"\n{Color.BG_YELLOW}{Color.BLUE} [ AUTHORIZATION REQUIRED ] {Color.RESET} Tool: {tool_name}")
        choice = input(f"Allow '{tool_name}' for {params.get('path')or params.get('command')}? (y/n/all): ").lower()
        func.debug(f"Request to calling Tool: {tool_name} : {params}")
        if choice == 'all':
            self.auto_authorized_tools.add(tool_name)
            return True
        return choice in ['y', 'yes']

    def _handle_agent_outputs(self, response: Dict[str, Any], current_agent: str, tool_name: Optional[str]) -> None:
        if thought := response.get("thought"):
            func.log(f"[{current_agent} THOUGHT]: {thought}")
        
        if msg_to_user := response.get("response_to_user"):
            func.out(f"\r\033[K{Color.GREEN}[{current_agent}]{Color.RESET} \n{msg_to_user}")
            
        if notes := response.get("notes"):
            self.agent_memory[current_agent]["notes"] = notes
            
        for m in self.agent_memory[current_agent]["messages_received"]:
            self.agent_memory[current_agent]["history"].append(m)
        self.agent_memory[current_agent]["history"].append({"from": "SELF", "thought": thought, "response": msg_to_user})
        self.agent_memory[current_agent]["messages_received"] = []

    def _update_stagnation_tracking(self, tool_name: Optional[str], params: Dict[str, Any]) -> None:
        current_fp = f"{tool_name}-{json.dumps(params)}"
        if current_fp == self.context["last_action_fp"]:
            self.context["repeat_count"] += 1
        else:
            self.context["repeat_count"] = 0
        self.context["last_action_fp"] = current_fp

    def _validate_target(self, target_raw: str, is_tool_empty: bool, current_agent: str, agent_config: Dict[str, Any]) -> str:
        if target_raw == "USER": return "USER"
        allowed_targets = agent_config.get("allowed_targets", ["STOP", "USER"])
        if target_raw and target_raw not in allowed_targets:
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": f"Invalid transition target '{target_raw}'. Allowed: {allowed_targets}."})
            return current_agent
        if is_tool_empty and not target_raw:
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": "You must either call a tool or transition."})
            return current_agent
        return target_raw

    def _handle_inter_agent_messaging(self, action: Dict[str, Any], target: str, current_agent: str) -> None:
        message_to_target = action.get("message_to_target")
        task_for_target = action.get("task_for_target", "")
        if message_to_target and target != "STOP" and target != current_agent:
            if target in self.agent_memory:
                self.agent_memory[target]["messages_received"].append({
                    "from": current_agent,
                    "message": message_to_target,
                    "task": task_for_target
                })