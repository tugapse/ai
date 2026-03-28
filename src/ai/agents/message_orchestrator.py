import json
from typing import Dict, Any, Optional
from .agent_tools import send_notification
import functions as func
from color import Color

MAX_ITERATIONS = 100
MANAGER_AGENT_ROLE = "management"

class MessageOrchestrator:
    def __init__(self, connector: Any, registry: Any, pipeline_config: Dict[str, Any]):
        """
        Initializes the central brain of the agentic system.
        Maintains global state, agent-specific memory, and the execution roadmap.
        """
        self.connector = connector
        self.registry = registry
        self.pipeline_config = pipeline_config
        self.agents = pipeline_config.get("agents", {})
        self.history = []
        self.auto_authorized_tools = set()
        
        # Global context for roadmap tracking and stagnation prevention
        self.context = {
            "tool_results": [], 
            "task": "",
            "plan": [], 
            "current_step_index": 1,
            "last_action_fp": None,
            "repeat_count": 0
        }
        
        # Agent Memory with both turn-based buffers and persistent history
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
        """
        The main autonomous loop. Orchestrates transitions between agents
        and manages the Human-In-The-Loop (HITL) gates.
        """
        func.log("Starting Pipeline Loop")
        current_agent = self.pipeline_config.get("entry_point", "MASTER")
        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        
        # Initial injection of the user request
        self.agent_memory[current_agent]["messages_received"].append({
            "from": "USER",
            "message": user_prompt,
            "task": user_prompt
        })
        
        for i in range(max_iterations):
            func.log(f"Execution loop iteration {i+1}/{max_iterations}. Agent: {current_agent}")
            
            # TASK PEEKING: Identify the most recent technical directive
            msgs = self.agent_memory[current_agent].get("messages_received", [])
            for msg in reversed(msgs):
                if msg.get("from") != "SYSTEM":
                    self.agent_memory[current_agent]["current_task"] = msg.get("task") or msg.get("message", "")
                    break
            
            active_task = self.agent_memory[current_agent].get("current_task", "")
            clean_task = " ".join(active_task.split())
            display_task = clean_task[:60] + ("..." if len(clean_task) > 60 else "")
            if not display_task: display_task = "an ongoing task..."
            
            # Status Bar
            func.out(f"{Color.BLUE}[ * ] {current_agent} is: {display_task}{Color.RESET}", end="", flush=True)

            agent_config = self.agents.get(current_agent, {}).copy()
            if not agent_config:
                func.error(f"Agent {current_agent} not defined in pipeline.")
                break
                
            # Tool Documentation Enrichment
            tool_docs = [self.registry.get_tool_info(t) for t in agent_config.get("tools", [])]
            agent_config["tool_descriptions"] = "\n".join(tool_docs)

            # Prepare Payload with full context and persistent history
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
                    "message": f"Your last output was invalid JSON. Error: {error_msg}. Please strictly fix your formatting, ensure all code quotes/newlines are escaped, and try again."
                })
                continue

            next_agent = self._process_agent_response(response, current_agent, agent_config)
            if next_agent is None or next_agent == "STOP": 
                func.log("Pipeline reached STOP state.")
                break
                
            current_agent = next_agent

    def _prepare_payload(self, user_prompt: str, current_agent: str) -> Dict[str, Any]:
        """
        Constructs the data packet for the LLM, including history, notes, 
        tool outcomes, and stagnation warnings.
        """
        known_fileS_locations = [
            res["parameters"].get("path") 
            for res in self.context["tool_results"] 
            if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"
        ]

        memory = self.agent_memory.get(current_agent, {})
        agent_config = self.agents.get(current_agent, {})
        is_management = agent_config.get("role") == MANAGER_AGENT_ROLE
        latest_task = "No specific task assigned."
        
        if memory["messages_received"]:
            latest_task = memory["messages_received"][-1].get("message", "Continue task.")
        
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
        
        # STAGNATION WARNING
        if self.context.get("repeat_count", 0) >= 2:
            payload["SYSTEM_ADVISORY"] = "WARNING: You are repeating tool calls. Change your strategy."
            
        return payload

    def _process_agent_response(self, response: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> str:
        """
        Parses LLM output, triggers tools, manages agent transitions, and handles
        special targets like 'USER'.
        """
        action = response.get("action", {})
        tool_name = action.get("tool_name")
        params = action.get("tool_parameters", {})
        agent_target = str(action.get("agent_target", "")).strip().upper()
        
        self.agent_memory[current_agent]["manifest"] = response.get("manifest", {})
        func.log(f"Agent manifest {Color.YELLOW}{response.get('manifest', {})}{Color.RESET}")
        
        self._handle_agent_outputs(response, current_agent, tool_name)
        self._update_stagnation_tracking(tool_name, params)
        
        # --- NEW: USER COMMUNICATION GATE ---
        if agent_target == "USER":
            question = action.get("message_to_target") or "The agent needs clarification."
            self.registry.execute_tool("send_notification", {"title": "Action Required", "message": f"{current_agent}: {question}."})
            func.out(f"\n{Color.BG_BLUE}{Color.NORMAL_GREEN} [ Question from {current_agent.lower()} ] {Color.RESET}")
            user_reply = input(f"{question}{Color.RESET}\n> ").strip()
            self.agent_memory[current_agent]["messages_received"].append({"from": "USER", "message": user_reply, "task": user_reply})
            return current_agent

        is_tool_empty = not tool_name or str(tool_name).lower() == "null"
        target = self._validate_target(agent_target, is_tool_empty, current_agent, agent_config)

        if target == "STOP": return "STOP"

        if not is_tool_empty:
            if not self._handle_tool_execution(tool_name, params, current_agent, agent_config):
                return current_agent # Stay on current agent if execution denied
                
            if not target or target == "NULL":
                return current_agent
                
        self._handle_inter_agent_messaging(action, target, current_agent)
        return target if target and target != "NULL" else current_agent

    def _update_stagnation_tracking(self, tool_name: Optional[str], params: Dict[str, Any]) -> None:
        """Original stagnation logic: Tracks if the agent is stuck repeating the same call."""
        current_fp = f"{tool_name}-{json.dumps(params)}"
        if current_fp == self.context["last_action_fp"]:
            self.context["repeat_count"] += 1
        else:
            self.context["repeat_count"] = 0
        self.context["last_action_fp"] = current_fp

    def _validate_target(self, target_raw: str, is_tool_empty: bool, current_agent: str, agent_config: Dict[str, Any]) -> str:
        """Original validation logic + auto-correct for idle loops."""
        if target_raw == "USER": return "USER"
        # TBD if target_raw == current_agent and is_tool_empty: return "STOP"
            
        allowed_targets = agent_config.get("allowed_targets", ["STOP", "USER"])
        if target_raw and target_raw not in allowed_targets:
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM",
                "message": f"Invalid transition target '{target_raw}'. Allowed: {allowed_targets}."
            })
            return current_agent
            
        if is_tool_empty and not target_raw:
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "SYSTEM", "message": "You must either call a tool or transition. Doing nothing is forbidden."
            })
            return current_agent
        return target_raw

    def _handle_agent_outputs(self, response: Dict[str, Any], current_agent: str, tool_name: Optional[str]) -> None:
        """Prints thoughts/responses and manages the history rotation to prevent amnesia."""
        if thought := response.get("thought"):
            func.log(f"[{current_agent} THOUGHT]: {thought}")
        
        if msg_to_user := response.get("response_to_user"):
            tool_str = f" {Color.BRIGHT_BLACK}[Tool: {tool_name}]{Color.RESET}" if tool_name and str(tool_name).lower() != "null" else ""
            func.out(f"\r\033[K{Color.GREEN}[{current_agent}]{Color.RESET}{tool_str} \n{msg_to_user}")
        else:
            func.out("\r\033[K", end="", flush=True)
            
        if notes := response.get("notes"):
            self.agent_memory[current_agent]["notes"] = notes
            
        # HISTORY ROTATION: Move turn messages to persistent history
        for m in self.agent_memory[current_agent]["messages_received"]:
            self.agent_memory[current_agent]["history"].append(m)
        self.agent_memory[current_agent]["history"].append({"from": "SELF", "thought": thought, "response": msg_to_user})
        self.agent_memory[current_agent]["messages_received"] = []

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], current_agent: str, agent_config: Dict[str, Any]) -> bool:
        if tool_name not in agent_config.get("tools", []):
            self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            return False

        # Check if the tool is already globally authorized for this session
        if tool_name in self.auto_authorized_tools:
            func.log(f"Auto-executing {tool_name} (Session Authorized)")
            is_authorized = True
        else:
            is_authorized = False
            
            # --- TERMINAL GATE ---
            if tool_name == "execute_command":
                func.out(f"\n{Color.BG_RED} [ TERMINAL REQUEST ] {Color.RESET} {Color.BOLD}{params.get('command')}{Color.RESET}")
                choice = input(f"Authorize? (y/n/all): ").lower()
                if choice == 'all':
                    self.auto_authorized_tools.add(tool_name)
                    is_authorized = True
                elif choice in ['y', 'yes']:
                    is_authorized = True

            # --- PATCH GATE ---
            elif tool_name == "patch_file":
                func.out(f"\n{Color.BG_CYAN} [ PATCH PROPOSAL ] {Color.RESET} {Color.NORMAL_CYAN}{params.get('path')}{Color.RESET}")
                func.out(f"{Color.RED}- {params.get('search')[:100]}...{Color.RESET}")
                func.out(f"{Color.GREEN}+ {params.get('replace')[:100]}...{Color.RESET}")
                choice = input(f"Apply patch? (y/n/all): ").lower()
                if choice == 'all':
                    self.auto_authorized_tools.add(tool_name)
                    is_authorized = True
                elif choice in ['y', 'yes']:
                    is_authorized = True

            # --- WRITE GATE ---
            elif tool_name == "write_file":
                func.out(f"\n{Color.BG_YELLOW} [ WRITE REQUEST ] {Color.RESET} Overwrite {params.get('path')}?")
                choice = input(f"Allow? (y/n/all): ").lower()
                if choice == 'all':
                    self.auto_authorized_tools.add(tool_name)
                    is_authorized = True
                elif choice in ['y', 'yes']:
                    is_authorized = True
            
            # Default for non-sensitive tools (read_file, etc.)
            else:
                is_authorized = True

        if not is_authorized:
            self.agent_memory[current_agent]["messages_received"].append({
                "from": "USER", 
                "message": f"DENIED: {tool_name} was blocked by user."
            })
            return False

        func.log(f"[TOOL CALL]: {tool_name}")
        result = self.registry.execute_tool(tool_name, params)
        
        self.context["tool_results"].append({"agent": current_agent, "tool": tool_name, "parameters": params, "result": result})
        
        if result.get("status") == "SUCCESS":
            self.context["current_step_index"] += 1
        
        self.agent_memory[current_agent]["messages_received"].append({"from": "SYSTEM", "result": result})
        return True

    def _handle_inter_agent_messaging(self, action: Dict[str, Any], target: str, current_agent: str) -> None:
        """Passes context between agents via messages_received."""
        message_to_target = action.get("message_to_target")
        task_for_target = action.get("task_for_target", "")
        if message_to_target and target != "STOP" and target != current_agent:
            if target in self.agent_memory:
                self.agent_memory[target]["messages_received"].append({
                    "from": current_agent,
                    "message": message_to_target,
                    "task": task_for_target
                })