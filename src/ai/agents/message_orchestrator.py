import os
import copy
import json
import re
from typing import Dict, Any, Optional

import functions as func
from color import Color
from terminal_ui import TerminalUI  # Importing your new shared UI class
from agents.agent_tools import _resolve_path  # Required for the Specialist to read file context

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
        self.format_error_count = 0  # Tracks consecutive JSON format failures
        
        # Specialist configuration for high-complexity tasks
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
            "action_history_fp": [],  # Sliding window for stagnation tracking
            "repeat_count": 0
        }
        
        self.agent_memory = {
            agent_name: {
                "notes": "System initialized.",
                "messages_received": [],
                "history": [],
                "current_task": "Waiting for tasks...",
                "manifest": {}
            }
            for agent_name in self.agents.keys()
        }

    def run_loop(self, user_prompt: str):
        TerminalUI.header("Pipeline Execution Start", "Unified Architect Orchestrator")
        
        current_agent = self.pipeline_config.get("entry_point", "MASTER")
        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        
        self.agent_memory[current_agent]["messages_received"].append({
            "from": "USER",
            "message": user_prompt,
            "task": user_prompt
        })
        
        for i in range(max_iterations):
            memory = self.agent_memory[current_agent]
            msgs = memory.get("messages_received", [])
            
            for msg in reversed(msgs):
                if msg.get("from") != "SYSTEM":
                    memory["current_task"] = msg.get("task") or msg.get("message")
                    break
            
            # Use the manifest's priority or fallback
            display_task = memory.get('manifest', {}).get("current_priority", "Analyzing objectives...")
            
            # Update the status (overwriting the thinking animation)
            TerminalUI.status(current_agent, display_task)

            # Deep copy to prevent accidental global registry modifications
            agent_config = copy.deepcopy(self.agents.get(current_agent, {}))
            if not agent_config:
                func.error(f"\n[!] Agent {current_agent} not defined.")
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
                self.format_error_count += 1
                if self.format_error_count >= 3:
                    TerminalUI.clear_line()
                    func.out(f"\n{Color.RED}⛔ Agent {current_agent} is stuck in a format loop. Halting pipeline.{Color.RESET}")
                    break

                TerminalUI.clear_line()
                func.out(f"\n{Color.RED}⚠ Format Error in {current_agent} (Strike {self.format_error_count}){Color.RESET}")
                error_msg = response.get("error", "Unknown error")
                memory["messages_received"].append({
                    "from": "SYSTEM",
                    "message": f"CRITICAL: Invalid JSON format. Error: {error_msg}. You must output ONLY valid JSON."
                })
                continue
            else:
                self.format_error_count = 0  # Reset strike counter on successful parse

            next_agent = self._process_agent_response(response, current_agent, agent_config)
            
            if next_agent is None or next_agent == "STOP": 
                TerminalUI.log_step("Pipeline reached STOP state.", "SUCCESS")
                break
                
            current_agent = next_agent

    def _prepare_payload(self, user_prompt: str, current_agent: str) -> Dict[str, Any]:
        known_files = [
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
            "conversation_history": memory.get("history", [])[-10:],
            "plan": self.context["plan"],
            "current_step": self.context["current_step_index"],
            "recent_outcomes": self._format_recent_outcomes(self.context["tool_results"][-3:]),
            "context": {"files_in_project": list(set(filter(None, known_files)))}
        }
        
        if self.context.get("repeat_count", 0) >= 3:
            payload["SYSTEM_ADVISORY"] = "WARNING: You are repeating the exact same tool calls. Change your strategy immediately to avoid an infinite loop."
            
        return payload

    def _format_recent_outcomes(self, outcomes: list) -> list:
        """Truncates massive tool outputs to protect the LLM context window."""
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
        action = response.get("action", {})
        tool_name = action.get("tool_name")
        params = action.get("tool_parameters", {})
        agent_target = str(action.get("agent_target", "")).strip().upper()
        
        self.agent_memory[current_agent]["manifest"] = response.get("manifest", {})
        self._handle_agent_outputs(response, current_agent)
        
        self._update_stagnation_tracking(tool_name, params)
        
        if agent_target == "USER":
            question = action.get("message_to_target") or "The agent needs clarification."
            TerminalUI.message(current_agent, question, Color.NORMAL_CYAN)
            user_reply = input(f"{Color.BLUE}❯ {Color.RESET}").strip()
            self.agent_memory[current_agent]["messages_received"].append({"from": "USER", "message": user_reply, "task": user_reply})
            return current_agent

        is_tool_empty = not tool_name or str(tool_name).strip().upper() == "NULL"
        target = self._validate_target(agent_target, is_tool_empty, current_agent, agent_config)

        if target == "STOP": return "STOP"

        if not is_tool_empty:
            if not self._handle_tool_execution(tool_name, params, current_agent, agent_config):
                return current_agent 
                
        self._handle_inter_agent_messaging(action, target, current_agent)
        return target if target and target != "NULL" else current_agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> bool:
        if tool_name not in agent_config.get("tools", []):
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            return False

        # Specialist Interceptor
        if tool_name in self.high_complexity_tools:
            TerminalUI.clear_line()
            func.out(f"{Color.NORMAL_CYAN}◈ Launching Specialist for {tool_name}...{Color.RESET}")
            
            goal = params.get("instructions") or params.get("content") or params.get("replace") or "Complete task."
            target_path = params.get("path", "unknown")
            
            refined_content = self._call_specialist_worker(
                role_description=self.high_complexity_tools[tool_name],
                path=target_path,
                goal=goal
            )
            
            # Map the specialist output to the correct tool parameter
            if tool_name == "patch_file":
                params["replace"] = refined_content
            else:
                params["content"] = refined_content

        # Authorization Gates
        if not self._gatekeeper(tool_name, params):
            self.agent_memory[current_agent]["messages_received"].append({"from": "USER", "message": f"DENIED: {tool_name} was blocked."})
            return False

        result = self.registry.execute_tool(tool_name, params)
        
        self.context["tool_results"].append({"agent": current_agent, "tool": tool_name, "parameters": params, "result": result})
        if result.get("status") == "SUCCESS":
            self.context["current_step_index"] += 1
        
        self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "result": result})
        return True

    def _call_specialist_worker(self, role_description: str, path: str, goal: str) -> str:
        # Fetch current file state to prevent the Specialist from writing blindly
        current_state = "File does not exist yet or is empty."
        try:
            resolved_path = _resolve_path({"path": path})
            if os.path.exists(resolved_path):
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    current_state = f.read()[:3000]  # Cap at 3000 chars to save context
        except Exception:
            pass # Fallback gracefully if path resolution fails

        worker_payload = {
            "task_context": f"File Target: {path}\n\nCurrent State:\n{current_state}\n\nGoal:\n{goal}",
            "instruction": "Output raw text only. Do not use markdown blocks or explanations."
        }
        raw_output_stream = self.connector.send_raw_request(worker_payload, system_prompt=role_description)
        return "".join(list(raw_output_stream)).strip()

    def _gatekeeper(self, tool_name: str, params: Dict[str, Any]) -> bool:
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

    def _handle_agent_outputs(self, response: Dict[str, Any], current_agent: str) -> None:
        if msg_to_user := response.get("response_to_user"):
            TerminalUI.message(current_agent, msg_to_user)
            
        memory = self.agent_memory[current_agent]
        memory["notes"] = response.get("notes", memory["notes"])
        
        # Cleanup messages for history
        for m in memory["messages_received"]:
            memory["history"].append(m)
        memory["history"].append({"from": "SELF", "thought": response.get("thought"), "response": msg_to_user})
        memory["messages_received"] = []

    def _update_stagnation_tracking(self, tool_name: Optional[str], params: Dict[str, Any]) -> None:
        # Create a fingerprint of the current action
        current_fp = f"{tool_name}-{json.dumps(params, sort_keys=True)}"
        
        self.context["action_history_fp"].append(current_fp)
        
        # Maintain a sliding window of the last 5 actions
        if len(self.context["action_history_fp"]) > 5:
            self.context["action_history_fp"].pop(0)
            
        # Count how many times this exact action happened recently
        occurrences = self.context["action_history_fp"].count(current_fp)
        
        if occurrences >= 3:
            self.context["repeat_count"] = occurrences
        else:
            self.context["repeat_count"] = 0

    def _validate_target(self, target_raw: str, is_tool_empty: bool, current_agent: str, agent_config: Dict[str, Any]) -> str:
        if target_raw == "USER": return "USER"
        allowed_targets = agent_config.get("allowed_targets", ["STOP", "USER"])
        if target_raw and target_raw not in allowed_targets:
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": f"Invalid transition target '{target_raw}'."})
            return current_agent
        if is_tool_empty and not target_raw:
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": "Call a tool or transition."})
            return current_agent
        return target_raw

    def _handle_inter_agent_messaging(self, action: Dict[str, Any], target: str, current_agent: str) -> None:
        msg = action.get("message_to_target")
        task = action.get("task_for_target", "")
        if msg and target != "STOP" and target != current_agent:
            if target in self.agent_memory:
                self.agent_memory[target]["messages_received"].append({
                    "from": current_agent,
                    "message": msg,
                    "task": task
                })