import json
from typing import Dict, Any
import functions as func
from color import Color

from .tool_registry import ToolRegistry
from .llm_connector import LLMConnector

MAX_ITTERATIONS = 100

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
                "messages_received": []
            }
            for agent_name in self.agents.keys()
        }

    def run_loop(self, user_prompt: str):
        func.log("Starting Pipeline Loop")
        current_agent = self.pipeline_config.get("entry_point", "MASTER")
        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITTERATIONS)
        
        self.agent_memory[current_agent]["messages_received"].append({
            "from": "USER",
            "message": user_prompt
        })
        
        for i in range(max_iterations):
            func.log(f"{Color.BLUE}Execution loop iteration {i+1}/{max_iterations}. Agent: {current_agent}{Color.RESET}")
            
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
                func.error(f"Agent {current_agent} failed.")
                break

            next_agent = self._process_agent_response(response, current_agent, agent_config)
            if next_agent is None or next_agent == "STOP": 
                func.log("Pipeline reached STOP state.")
                break
                
            current_agent = next_agent

    def _prepare_payload(self, user_prompt: str, current_agent: str) -> Dict[str, Any]:
        current_step = next((s for s in self.context["plan"] if s["step"] == self.context["current_step_index"]), {})
        known_files = [res["parameters"].get("path") for res in self.context["tool_results"] if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"]

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
        if thought := response.get("thought"):
            func.out(f"\n{Color.BOLD}[{current_agent} THOUGHT]:{Color.RESET} {thought}")
        
        if msg_to_user := response.get("response_to_user"):
            func.out(f"{Color.PURPLE}Message: {msg_to_user}{Color.RESET}")
        
        if notes := response.get("notes"):
            func.out(f"{Color.NORMAL_CYAN}Notes saved.{Color.RESET}")
            self.agent_memory[current_agent]["notes"] = notes
            
        # Clear read messages
        self.agent_memory[current_agent]["messages_received"] = []

        action = response.get("action", {})
        tool_name = action.get("tool_name")
        
        current_fp = f"{tool_name}-{json.dumps(action.get('tool_parameters'))}"
        if current_fp == self.context["last_action_fp"]:
            self.context["repeat_count"] += 1
        else:
            self.context["repeat_count"] = 0
        self.context["last_action_fp"] = current_fp
        
        agent_target = action.get("agent_target")
        if not agent_target or str(agent_target).strip().lower() == "null":
            target_raw = ""
        else:
            target_raw = str(agent_target).strip().upper()
            
        allowed_targets = agent_config.get("allowed_targets", ["STOP"])
        
        if target_raw and target_raw not in allowed_targets:
            func.error(f"Agent {current_agent} tried to transition to {target_raw}, which is not allowed. Allowed: {allowed_targets}")
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM",
                "message": f"Invalid transition target '{target_raw}'. You must choose from: {allowed_targets}. If the user request is completely fulfilled, transition to STOP."
            })
            return current_agent
            
        target = target_raw
        
        is_tool_empty = not tool_name or str(tool_name).lower() == "null"

        if is_tool_empty and not target:
            func.error(f"Agent {current_agent} did not use a tool or specify a target.")
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM",
                "message": "You must either call a tool or transition to another agent. If you are finished, transition to STOP. Doing nothing is not allowed."
            })
            return current_agent

        if target == "STOP" and is_tool_empty:
            msg = response.get("response_to_user", "")
            if not any(x in msg for x in ["/", ".py", ":", "["]):
                func.error("REJECTION: Agent tried to stop without proof.")
                self.agent_memory[current_agent]["messages_received"].append({
                    "from": "SYSTEM",
                    "message": "REJECTION: Provide File:Line proof in 'response_to_user' before stopping."
                })
                return current_agent
            return "STOP"

        if not is_tool_empty:
            if tool_name not in agent_config.get("tools", []):
                func.error(f"Agent {current_agent} tried to use unauthorized tool: {tool_name}")
                self.agent_memory[current_agent]["messages_received"].append({
                    "from": "SYSTEM",
                    "message": f"Unauthorized tool '{tool_name}'. Allowed tools: {agent_config.get('tools', [])}"
                })
                return current_agent
                
            params = action.get("tool_parameters", {})
            func.out(f"{Color.BLUE}[TOOL CALL]: {tool_name}{Color.RESET}")
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
                
            if not target or target == "NULL":
                return current_agent
                
        message_to_target = action.get("message_to_target")
        if message_to_target and target != "STOP" and target != current_agent:
            if target in self.agent_memory:
                self.agent_memory[target]["messages_received"].append({
                    "from": current_agent,
                    "message": message_to_target
                })
                func.out(f"{Color.BRIGHT_CYAN}[MESSAGE] {current_agent} -> {target}: {message_to_target}{Color.RESET}")

        return target if target and target != "NULL" else current_agent