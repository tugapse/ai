import json
from typing import Dict, Any, Optional
import functions as func
from color import Color

from .tool_registry import ToolRegistry
from .llm_connector import LLMConnector

MAX_ITERATIONS = 100

class MessageOrchestrator:
    def __init__(self, connector: LLMConnector, registry: ToolRegistry, pipeline_config: Dict[str, Any]):
        self.connector = connector
        self.registry = registry
        self.pipeline_config = pipeline_config
        self.agents = pipeline_config.get("agents", {})
        self.history = []
        
        self.context = {
            "tool_results": [], 
            "task":"",
            "plan": [], 
            "current_step_index": 1,
            "last_action_fp": None,
            "repeat_count": 0
        }
        
        self.agent_memory = {
            agent_name: {
                "notes": "System initialized.",
                "messages_received": [],
                "current_task": "Waiting for tasks..."
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
                    self.agent_memory[current_agent]["current_task"] = msg.get("task") or msg.get("message", "")
                    break
            
            active_task = self.agent_memory[current_agent].get("current_task", "")
            clean_task = " ".join(active_task.split())
            display_task = clean_task[:60] + ("..." if len(clean_task) > 60 else "")
            if not display_task: display_task = "an ongoing task..."
            
            func.out(f"\r\033[K{Color.BLUE}[ * ] {current_agent} is working on: {display_task}{Color.RESET}", end="", flush=True)

            # Use a copy so we don't permanently modify the base config
            agent_config = self.agents.get(current_agent, {}).copy()
            if not agent_config:
                func.error(f"Agent {current_agent} not defined in pipeline.")
                break
                
            # Enrich config with actual tool descriptions
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
                func.error(f"Agent {current_agent} failed: {error_msg}. Retrying...")
                self.agent_memory[current_agent]["messages_received"].append({
                    "from": "SYSTEM",
                    "message": f"Your last output was invalid JSON. Error: {error_msg}. Please strictly fix your formatting, ensure all code quotes and newlines are properly escaped, and try again."
                })
                continue

            next_agent = self._process_agent_response(response, current_agent, agent_config)
            if next_agent is None or next_agent == "STOP": 
                func.log("Pipeline reached STOP state.")
                break
                
            current_agent = next_agent

    def _prepare_payload(self, user_prompt: str, current_agent: str) -> Dict[str, Any]:
        current_step = next((s for s in self.context["plan"] if s["step"] == self.context["current_step_index"]), {})
        known_files = [
            res["parameters"].get("path") 
            for res in self.context["tool_results"] 
            if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"
        ]

        memory = self.agent_memory.get(current_agent, {})

        payload = {
            "user_prompt": user_prompt,
            "agent_notes": memory.get("notes"),
            "messages_received": memory.get("messages_received"),
            "plan": self.context["plan"],
            "current_step": self.context["current_step_index"],
            "step_objective": current_step.get("task", "Executing analysis"),
            "recent_outcomes": self.context["tool_results"][-3:],
            "context": {"files_in_project": list(set(filter(None, known_files)))}
        }
        
        # STAGNATION WARNING
        if self.context.get("repeat_count", 0) >= 2:
            payload["SYSTEM_ADVISORY"] = "WARNING: You are repeating tool calls. Change your search strategy or move directories."
            
        return payload

    def _process_agent_response(self, response: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> str:
        action = response.get("action", {})
        tool_name = action.get("tool_name")
        params = action.get("tool_parameters", {})
        agent_target = action.get("agent_target")
        
        self._handle_agent_outputs(response, current_agent, tool_name)

        self._update_stagnation_tracking(tool_name, params)
        
        target_raw = "" if not agent_target or str(agent_target).strip().lower() == "null" else str(agent_target).strip().upper()
        is_tool_empty = not tool_name or str(tool_name).lower() == "null"
        
        target = self._validate_target(target_raw, is_tool_empty, current_agent, agent_config)
        if target == current_agent and target_raw != current_agent:
            return current_agent

        if target == "STOP":
            return "STOP"

        if not is_tool_empty:
            if not self._handle_tool_execution(tool_name, params, current_agent, agent_config):
                return current_agent
                
            if not target or target == "NULL":
                return current_agent
                
        self._handle_inter_agent_messaging(action, target, current_agent)

        return target if target and target != "NULL" else current_agent

    def _update_stagnation_tracking(self, tool_name: Optional[str], params: Dict[str, Any]) -> None:
        current_fp = f"{tool_name}-{json.dumps(params)}"
        if current_fp == self.context["last_action_fp"]:
            self.context["repeat_count"] += 1
        else:
            self.context["repeat_count"] = 0
        self.context["last_action_fp"] = current_fp

    def _validate_target(self, target_raw: str, is_tool_empty: bool, current_agent: str, agent_config: Dict[str, Any]) -> str:
        # AUTO-CORRECT: If the agent targets itself with no tool, it implies it wants to yield to the user.
        if target_raw == current_agent and is_tool_empty:
            target_raw = "STOP"
            
        allowed_targets = agent_config.get("allowed_targets", ["STOP"])
        
        if target_raw and target_raw not in allowed_targets:
            func.error(f"Agent {current_agent} tried to transition to {target_raw}, which is not allowed. Allowed: {allowed_targets}")
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM",
                "message": f"Invalid transition target '{target_raw}'. You must choose from: {allowed_targets}. If the user request is completely fulfilled, transition to STOP."
            })
            return current_agent
            
        if is_tool_empty and not target_raw:
            func.error(f"Agent {current_agent} did not use a tool or specify a target.")
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM",
                "message": "You must either call a tool or transition to another agent. If you are finished, transition to STOP. Doing nothing is not allowed."
            })
            return current_agent

        return target_raw

    def _handle_agent_outputs(self, response: Dict[str, Any], current_agent: str, tool_name: Optional[str]) -> None:
        if thought := response.get("thought"):
            func.log(f"[{current_agent} THOUGHT]: {thought}")
        
        if msg_to_user := response.get("response_to_user"):
            tool_str = f" {Color.BRIGHT_BLACK}[Tool: {tool_name}]{Color.RESET}" if tool_name and str(tool_name).lower() != "null" else ""
            func.out(f"\r\033[K{Color.GREEN}[{current_agent}]{Color.RESET}{tool_str} \n{msg_to_user}\n")
        else:
            func.out("\r\033[K", end="", flush=True)
            
        if notes := response.get("notes"):
            func.log("Notes saved.")
            self.agent_memory[current_agent]["notes"] = notes
            
        # Clear read messages
        self.agent_memory[current_agent]["messages_received"] = []

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> bool:
        if tool_name not in agent_config.get("tools", []):
            func.error(f"Agent {current_agent} tried to use unauthorized tool: {tool_name}")
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM",
                "message": f"Unauthorized tool '{tool_name}'. Allowed tools: {agent_config.get('tools', [])}"
            })
            return False
            
        # --- HUMAN IN THE LOOP (HITL) SENSITIVE TOOL GUARD ---
        if tool_name in ["write_file", "delete_item"]:
            target_path = params.get("path", "unknown path")
            func.out(f"\n{Color.BG_YELLOW}{Color.NORMAL_BLACK} [ ACTION REQUIRED ] {Color.RESET} {Color.YELLOW}Agent '{current_agent}' wants to execute '{tool_name}' on '{target_path}'.{Color.RESET}")
            user_auth = input(f"Allow this action? (y/n): ").strip().lower()
            
            if user_auth not in ['y', 'yes']:
                func.out(f"{Color.RED}Action denied by user.{Color.RESET}")
                self.agent_memory[current_agent]["messages_received"].append({
                    "from": "USER",
                    "message": f"I denied your request to execute '{tool_name}' on '{target_path}'. Please explain why you need to do this, or ask me for clarification."
                })
                return False

        func.log(f"[TOOL CALL]: {tool_name}")
        result = self.registry.execute_tool(tool_name, params)
        
        self.context["tool_results"].append({
            "step": self.context["current_step_index"],
            "agent": current_agent,
            "tool": tool_name, 
            "parameters": params,
            "result": result.get("output", result) 
        })
        
        if result.get("status") == "SUCCESS":
            self.context["current_step_index"] += 1
            func.log(f"Step completed. Current Index: {self.context['current_step_index']}")

        return True

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
                func.log(f"[MESSAGE] {current_agent} -> {target}: {message_to_target}")