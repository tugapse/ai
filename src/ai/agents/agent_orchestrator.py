import os
import copy
import json
import threading
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, List

from ai.agents.llm_connector import LLMConnector
import ai.functions as func
from ai.config import ProgramConfig, ProgramSetting
from ai.color import Color
from ai.agents.agent_io import AgentIO, AgentEvent, AgentEventType, ConsoleIO, PERMISSION_ALWAYS, PERMISSION_YES
from ai.agents.specialist_manager import SpecialistManager
from ai.agents.memory_manager import AgentMemory, MemoryManager
from ai.agents.context_sentinel import ContextSentinel
from ai.agents.session_manager import AgentSessionManager
from ai.core.events import Events
from ai.services.directory_manager import DirectoryManager
from ai.services.module_registry import ModuleRegistry
from ai.services.process_manager import ProcessManager
from ai.tools.mcp_bridge import MCPBridge
from ai.tools.tool_registry import ToolRegistry

MAX_ITERATIONS = 100
MANAGER_AGENT_ROLE = "management"

STOP_SIGNAL = "STOP"
MASTER_AGENT = "MASTER"
USER_TARGET = "USER"
# Alias any agent may target to mean "itself"; resolved to the acting agent's name.
SELF_TARGET = "SELF"
DONE_SIGNAL = "DONE"

# Fallback list of tools that require explicit user authorization (HIL).
# The effective list comes from the HIL_TOOLS setting in config.json.
GATED_TOOLS = ["execute_command"]


def get_hil_tools() -> List[str]:
    """Returns the tools that need human approval, from the HIL_TOOLS setting."""
    try:
        configured = ProgramConfig.get_current().get(ProgramSetting.HIL_TOOLS)
    except Exception:
        configured = None
    if isinstance(configured, (list, tuple)):
        return list(configured)
    return list(GATED_TOOLS)


@dataclass
class TurnResult:
    """Outcome of a single ``run_loop`` call.

    Attributes:
        reason: Why the loop returned: 'done', 'awaiting_user', 'cancelled',
            'max_iterations' or 'error'.
        agent: The agent that was active when the loop returned.
        message: The last response_to_user, or the question when awaiting the user.
        iterations: Number of iterations executed in this call.
    """
    reason: str
    agent: Optional[str] = None
    message: str = ""
    iterations: int = 0

class AgentOrchestrator(Events):
    """
    Orchestrates multi-agent execution, routing, and state management.
    Integrates short-term context protection and long-term session persistence.
    """
    EVENT_BEFORE_LLM_REQUEST = "before_llm_request"
    EVENT_AFTER_LLM_REQUEST = "after_llm_request"

    def __init__(self, llm_connector: LLMConnector, tool_registry: ToolRegistry, pipeline_config: Dict[str, Any], module_registry: ModuleRegistry, io: Optional[AgentIO] = None):
        """
        Initializes the AgentOrchestrator with necessary components.

        Args:
            llm_connector: The connector responsible for LLM communication.
            tool_registry: Registry holding all available tools.
            pipeline_config: Configuration dictionary defining the agent pipeline.
            module_registry: Registry for loading external functional modules.
            io: Output/input channel. Defaults to the classic terminal ``ConsoleIO``.
        """
        super().__init__()
        self.io: AgentIO = io or ConsoleIO()
        self.cancel_event = threading.Event()
        self.llm_connector = llm_connector
        self.tool_registry = tool_registry
        self.pipeline_config = pipeline_config
        self.module_registry = module_registry
        
        self.agents = pipeline_config.get("agents", {})
        self.auto_authorized_tools = set()
        self.format_error_count = 0

        # Specialized Managers
        self.specialist_manager = SpecialistManager(
            self.llm_connector, 
            {"generate_doc": "Technical Writer. Deep-dive documentation."}
        )
        self.context_sentinel = ContextSentinel(
            self.llm_connector, 
            threshold=0.9, 
            max_tokens=self.llm_connector.get_context_limit(),
            buffer=self.llm_connector.get_max_tokens()
        )

        self.mcp_bridge = MCPBridge(self.tool_registry)
        # Load external servers from config
        directory = DirectoryManager()
        mcp_config = os.path.join(directory.get_user_config_directory(), "mcp_config.json")
        if not os.path.exists(mcp_config):
            func.log("[MCP] config not found on user directory. Using system config.", level="WARN")
            mcp_config = os.path.join(directory.get_system_config_dir(), "mcp_config.json")
        
        self.mcp_bridge.load_from_config(mcp_config)
        
        # Memory State
        self.memory = MemoryManager(list(self.agents.keys()))
        self.vector_memory = None
        
        # Session State (Initialized in run_loop)
        self.session_manager = None
        self.session_id = None

    def emit(self, event_type: AgentEventType, agent: Optional[str] = None, text: str = "", **data):
        """Shortcut to send an event through the I/O channel."""
        self.io.emit(AgentEvent(type=event_type, agent=agent, text=text, data=data))

    def cancel(self):
        """Requests the running loop to stop at the next safe point (thread-safe)."""
        self.cancel_event.set()
        # Only stop the current generation stream. Do NOT call request_shutdown():
        # some engines (GGUF) unload the model there, which would kill the session.
        llm = getattr(self.llm_connector, "llm", None)
        stop_event = getattr(llm, "stop_generation_event", None)
        if stop_event is not None:
            stop_event.set()

    def close(self):
        """Shuts down external resources (MCP server processes, e.g. Playwright's browser)."""
        bridge = getattr(self, "mcp_bridge", None)
        if bridge is not None and hasattr(bridge, "close"):
            try:
                bridge.close(timeout=3)
            except Exception as e:
                func.debug(f"Orchestrator: MCP shutdown failed: {e}")

    def reset_state(self):
        """Clears all in-memory agent state (used when starting a fresh session)."""
        self.memory = MemoryManager(list(self.agents.keys()))
        self.auto_authorized_tools = set()
        self.format_error_count = 0
        self._original_request = None

    def run_loop(self, user_prompt: str, session_id: str) -> TurnResult:
        """
        Main execution loop. Hydrates session if available, otherwise starts fresh.
        The user prompt is always delivered to the active agent, so resuming a
        session with a new message continues the conversation.

        Args:
            user_prompt: The initial or ongoing prompt from the user.
            session_id: The unique identifier for the current session.

        Returns:
            A TurnResult describing why the loop stopped.
        """
        self.cancel_event.clear()
        self._awaiting_user: Optional[str] = None
        self._last_message = ""
        self.session_id = session_id
        self.session_manager = AgentSessionManager(session_id)
        self._initialize_modules()

        start_iteration, current_agent = self._get_saved_session(session_id=session_id, user_prompt=user_prompt)

        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        end_iteration = start_iteration + max_iterations
        ProcessManager.set_state("mode", "agent")
        executed = 0

        for i in range(start_iteration, end_iteration):
            if self.cancel_event.is_set():
                return self._finish("cancelled", current_agent, executed)

            # Agent state validation at the start of the loop
            if current_agent in [None, STOP_SIGNAL]:
                self.emit(AgentEventType.INFO, text="Pipeline execution finished.", status="SUCCESS")
                return self._finish("done", current_agent, executed)
            ProcessManager.set_state("agent_turn", i)
            ProcessManager.set_state("agent_max_turn", end_iteration)

            agent_mem = self.memory.get_agent_memory(current_agent)
            if not agent_mem:
                # This can happen if an invalid agent is targeted.
                self.emit(AgentEventType.ERROR, current_agent, f"Agent '{current_agent}' not found in memory or is invalid. Stopping.")
                return self._finish("error", current_agent, executed)

            # Context Update
            for msg in reversed(agent_mem.messages_received):
                if msg.get("from") != "SYSTEM":
                    agent_mem.current_task = msg.get("task") or msg.get("message")
                    break

            # Assemble Tools and Prepare Payload
            agent_config = copy.deepcopy(self.agents.get(current_agent, {}))
            if not agent_config:
                self.emit(AgentEventType.ERROR, current_agent, f"Agent {current_agent} undefined.")
                return self._finish("error", current_agent, executed)

            active_tools = self._assemble_agent_tools(current_agent)
            agent_config["tools"] = self._allowed_tools(current_agent)
            agent_config["allowed_targets"] = self._targets_for_prompt(current_agent, agent_config)
            agent_config["tool_descriptions"] = "\n".join([self.tool_registry.get_tool_info(name) for name in active_tools.keys()])

            payload = self._prepare_payload(user_prompt, current_agent)
            payload, was_compressed = self.context_sentinel.enforce_limits(
                current_agent, self.memory, payload, vector_memory=self.vector_memory
            )
            ProcessManager.set_state("agent_payload", payload)

            self.emit(
                AgentEventType.STATUS, current_agent,
                str(agent_mem.manifest.get("current_priority", agent_mem.current_task) or ""),
                iteration=i - start_iteration + 1, max_iterations=max_iterations,
                context_pressure=getattr(self.context_sentinel, "last_pressure", None),
                fresh=False,  # progress update; the agent's own status arrives with its response
            )

            if was_compressed:
                self.emit(AgentEventType.INFO, current_agent, f"Sentinel: Context distilled for {current_agent}", status="INFO")

            self.trigger("before_llm_request", {"agent": current_agent, "payload_preview": {k: v for k, v in payload.items() if k not in ['messages_received', 'conversation_history']}})
            self.emit(AgentEventType.LLM_REQUEST, current_agent)
            response = self.llm_connector.send_request(payload, agent_config["prompt_file_path"], agent_config=agent_config)
            self.trigger("after_llm_request", {"agent": current_agent, "response": response})
            executed += 1

            # A cancelled generation yields a truncated (unusable) response: drop it.
            if self.cancel_event.is_set():
                return self._finish("cancelled", current_agent, executed)

            if response.get("status") == "FAILED" and response.get("api_error"):
                # The provider already retried transient errors; don't blame the model's format.
                hint = " Session saved: send a message (e.g. 'continue') to retry." if response.get("transient") else ""
                self.emit(AgentEventType.ERROR, current_agent, f"{response.get('error')}{hint}")
                return self._finish("api_error", current_agent, executed, message=response.get("error", ""))

            if response.get("status") == "FAILED":
                if not self._handle_format_error(current_agent, response.get("error") or "Unknown parsing error."):
                    return self._finish("error", current_agent, executed)
                continue

            self.format_error_count = 0

            # Process Response and Route
            next_agent = self._process_agent_response(response, current_agent, agent_config)

            # PERSISTENCE: Commit state before moving to the next iteration
            self.session_manager.commit(self._capture_state(next_agent, i + 1, user_prompt))

            if self._awaiting_user is not None:
                return self._finish("awaiting_user", current_agent, executed, message=self._awaiting_user)

            if next_agent == DONE_SIGNAL:
                func.log(f"Cycle complete for {current_agent}. Clearing memory.", level="WARN")
                self.memory.clear(current_agent)
                next_agent = MASTER_AGENT

            current_agent = next_agent

        if current_agent in [None, STOP_SIGNAL]:
            self.emit(AgentEventType.INFO, text="Pipeline execution finished.", status="SUCCESS")
            return self._finish("done", current_agent, executed)

        self.emit(AgentEventType.ERROR, current_agent, f"Iteration budget exhausted ({max_iterations}).")
        return self._finish("max_iterations", current_agent, executed)

    def _finish(self, reason: str, agent: Optional[str], executed: int, message: Optional[str] = None) -> TurnResult:
        """Builds the TurnResult returned by run_loop."""
        return TurnResult(
            reason=reason,
            agent=agent,
            message=self._last_message if message is None else message,
            iterations=executed,
        )

    def _get_saved_session(self, session_id: str, user_prompt: str)->tuple[int, str]:
        """
        Retrieves the state of a saved session or initializes a new one, then
        delivers the user prompt to the active agent.

        Args:
            session_id: The ID of the session to load.
            user_prompt: The current user prompt.

        Returns:
            A tuple containing the starting iteration count and the initial agent.
        """
        entry_point = self.pipeline_config.get("entry_point", MASTER_AGENT)
        current_agent = entry_point
        start_iteration = 0

        session_state = self.session_manager.get_session() if self.session_manager else None
        if session_state:
            self.emit(AgentEventType.HEADER, text=f"Resuming Session: {session_id}", subtitle="Sentinel Architect", resumed=True)
            self._apply_state(session_state)
            self._original_request = session_state.get("user_request") or user_prompt
            current_agent = session_state.get("current_agent", entry_point)
            start_iteration = session_state.get("iteration", 0)

            # State integrity check: terminal signals or agents missing from the pipeline restart at the entry point.
            if current_agent not in self.agents:
                if current_agent not in [None, STOP_SIGNAL, DONE_SIGNAL, USER_TARGET]:
                    func.log(f"Stale agent '{current_agent}' in session. Resetting to entry point.", level="WARN")
                current_agent = entry_point

            func.log(f"Orchestrator: State re-inflated. Resuming as {current_agent} at iteration {start_iteration}")
        else:
            self.emit(AgentEventType.HEADER, text="Pipeline Execution Start", subtitle="Agent Orchestrator", resumed=False)
            self.reset_state()
            self._original_request = user_prompt

        current_agent = current_agent or MASTER_AGENT
        if user_prompt:
            self.memory.add_message_to_agent(current_agent, {
                "from": "USER", "message": user_prompt, "task": user_prompt
            })

        return start_iteration, current_agent

    def _capture_state(self, next_agent: str, iteration: int,user_request: str) -> Dict[str, Any]:
        """
        Serializes current memory and orchestration metadata for session persistence.

        Args:
            next_agent: The agent scheduled for the next turn.
            iteration: The iteration number after the current turn.
            user_request: The current user request (the session keeps its original one).

        Returns:
            A dictionary containing the serialized state.
        """
        return {
            "user_request": getattr(self, "_original_request", None) or user_request,
            "last_user_message": user_request,
            "current_agent": next_agent,
            "iteration": iteration,
            "memory": self.memory.serialize(),
            "context_plan": self.memory.context.plan,
            "step_index": self.memory.context.current_step_index,
            "auto_authorized_tools": list(self.auto_authorized_tools)
        }

    def _apply_state(self, state: Dict[str, Any]):
        """
        Injects serialized state back into active managers, restoring the pipeline state.

        Args:
            state: The dictionary containing the saved session state.
        """
        self.memory.load_state(state.get("memory", {}))
        self.memory.context.plan = state.get("context_plan", [])
        self.memory.context.current_step_index = state.get("step_index", 0)
        self.auto_authorized_tools = set(state.get("auto_authorized_tools", []))

    def _allowed_tools(self, agent_name: str) -> List[str]:
        """
        Returns the tool names an agent may use: its pipeline allow-list plus all MCP tools.
        Never mutates the pipeline configuration.

        Args:
            agent_name: The name of the agent.

        Returns:
            A de-duplicated list of tool names, preserving order.
        """
        allowed = list(self.agents.get(agent_name, {}).get("tools", []))
        if hasattr(self, "mcp_bridge"):
            allowed.extend(self.mcp_bridge.server_schemas.keys())
        return list(dict.fromkeys(allowed))

    def _assemble_agent_tools(self, agent_name: str) -> Dict[str, Callable]:
        """
        Assembles the set of tools available to a specific agent based on its configuration and system capabilities.

        Args:
            agent_name: The name of the agent requesting the tool set.

        Returns:
            A dictionary mapping tool names to their callable functions.
        """
        allowed = set(self._allowed_tools(agent_name))
        tool_pool = copy.copy(self.tool_registry.get_all_tools())
        return {n: f for n, f in tool_pool.items() if n in allowed}

    def _prepare_payload(self, user_prompt: str, agent: str) -> Dict[str, Any]:
        """
        Constructs the payload for the LLM, including context, history, and recent outcomes.

        Args:
            user_prompt: The current user prompt.
            agent: The agent for whom the payload is being prepared.

        Returns:
            A dictionary structured for the LLM request.

        Raises:
            ValueError: If the agent's memory cannot be found.
        """
        mem = self.memory.get_agent_memory(agent)
        if not mem :
            raise ValueError(f"Agent memory not found for {agent}")
        
        known_files = [
            res["parameters"].get("path")
            for res in self.memory.context.tool_results
            if res["tool"] == "write_file" and res["result"].get("status") == "SUCCESS"
        ]
        is_mgr = self.agents.get(agent, {}).get("role") == MANAGER_AGENT_ROLE
        
        payload = {
            "objective": user_prompt if is_mgr else (mem.messages_received[-1].get("message", "Continue.") if mem.messages_received else "Continue."),
            "agent_notes": mem.notes,
            "messages_received": mem.messages_received,
            "conversation_history": mem.history[-10:],
            "plan": self.memory.context.plan, # FIXME We are not fetching the plan from the response nor injecting it into the payload.
            "current_step": self.memory.context.current_step_index,
            "recent_outcomes": self._format_recent_outcomes(self.memory.context.tool_results[-3:]),
            "context": {"files_in_project": list(set(filter(None, known_files)))}
        }
        
        if self.vector_memory and len(mem.messages_received) % 4 == 0:
            query = mem.current_task or user_prompt
            payload["long_term_memory"] = "\n- ".join(self.vector_memory.retrieve_memories(query, top_k=5))
        return payload

    def _process_agent_response(self, response: Dict[str, Any], agent: str, config: Dict[str, Any]) -> str:
        """
        Processes the LLM response to determine the next action, target, or state transition.

        Args:
            response: The raw response dictionary from the LLM connector.
            agent: The agent that generated the response.
            config: The configuration dictionary for the current agent.

        Returns:
            The name of the next agent to execute, or the current agent if no transition occurs.
        """
        action = response.get("action", {})
        tool_name, params = action.get("tool_name"), action.get("tool_parameters", {})
        target = self._resolve_target_alias(str(action.get("agent_target", "")).strip().upper(), agent)

        # Status first: the agent's current priority from THIS response, shown before its
        # message and before any permission request (it used to lag one step behind).
        manifest = response.get("manifest") or {}
        priority = str(manifest.get("current_priority") or "").strip()
        agent_mem = self.memory.get_agent_memory(agent)
        previous = str((agent_mem.manifest if agent_mem else {}).get("current_priority") or "").strip()
        if priority and priority != previous:
            self.emit(AgentEventType.STATUS, agent, priority, phase=str(manifest.get("phase") or ""), fresh=True)

        if thought := response.get("thought"):
            if ProgramConfig.get_current().get(ProgramSetting.AGENT_THOUGHT, False): 
                self.emit(AgentEventType.THOUGHT, agent, thought)

        msg = response.get("response_to_user", "")
        if msg:
            # if self.vector_memory: self.vector_memory.add_memory(msg, agent, "communication")
            self._last_message = msg
            self.emit(AgentEventType.MESSAGE, agent, msg)

        self.memory.update_agent_history_and_notes(agent, response)
        self.memory.check_stagnation(tool_name, params)

        if target == USER_TARGET:
            # A tool call in the same response must still run before handing back to the user
            # (it used to be silently skipped while the agent reported it as done).
            if tool_name and str(tool_name).upper() != "NULL":
                self._handle_tool_execution(tool_name, params, agent, config)
            question = action.get("message_to_target")
            prompt = question or msg or "Clarification required."
            # If the agent only handed control back after answering, its response was
            # already shown; don't print a generic question on top of it.
            if question or not msg:
                self.emit(AgentEventType.QUESTION, agent, prompt)
            if self.io.blocking_user_input:
                reply = self.io.request_user_input(agent, prompt)
                self.memory.add_message_to_agent(agent, {"from": "USER", "message": reply, "task": reply})
            else:
                # Non-blocking UIs: end the turn; the next user message is the reply.
                self._awaiting_user = prompt
            return agent

        is_empty = not tool_name or str(tool_name).upper() == "NULL"
        validated_target = self._validate_target(target, is_empty, agent, config)

        if not is_empty and validated_target != STOP_SIGNAL:
            if not self._handle_tool_execution(tool_name, params, agent, config):
                return agent

        msg_to_target = action.get("message_to_target")
        if msg_to_target and validated_target not in [STOP_SIGNAL, agent]:
            self.memory.add_message_to_agent(validated_target, {"from": agent, "message": msg_to_target, "task": action.get("task_for_target", "")})

        return validated_target or agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], agent: str, config: Dict[str, Any]) -> bool:
        """
        Executes a tool, handling specialist overrides and authorization checks.

        Args:
            tool_name: The name of the tool to execute.
            params: The parameters passed to the tool.
            agent: The agent attempting to use the tool.
            config: The agent's configuration.

        Returns:
            True if the tool executed successfully, False otherwise.
        """
        if tool_name not in config.get("tools", []):
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            func.debug(f"Agent {agent} attempted to use unauthorized tool: {tool_name} , allowed tools: {config.get('tools', [])}", level="WARN")
            self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                      result={"status": "UNAUTHORIZED", "error": f"'{tool_name}' is not allowed for {agent}"})
            return False

        if self.specialist_manager.is_specialist_tool(tool_name):
            self.emit(AgentEventType.SPECIALIST, agent, tool=tool_name)
            content = self.specialist_manager.invoke(tool_name, params)
            params["replace" if tool_name == "patch_file" else "content"] = content

        if not self._gatekeeper(tool_name, params, agent):
            self.memory.add_message_to_agent(agent, {"from": "USER", "message": "Access Denied."})
            self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                      result={"status": "DENIED", "error": "User denied execution."})
            return False

        result = self.tool_registry.execute_tool(tool_name, params)
        self.memory.record_tool_result(agent, tool_name, params, result)
        self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                  result=result if isinstance(result, dict) else {"status": "SUCCESS", "result": result})
        return True

    def _initialize_modules(self):
        """
        Initializes all registered modules, centralizing their tools in the ToolRegistry.
        """
        for module_name, mod in self.module_registry.items():
            if not mod:
                continue

            instance = mod.get_instance()

            if module_name == "vector_memory":
                self.vector_memory = instance
                func.log(f"VectorMemory: {'CONNECTED' if self.vector_memory else 'DISABLED'}")

            if instance and hasattr(instance, 'tools') and hasattr(instance.tools, 'get_tools'):
                module_tools = instance.tools.get_tools()
                for tool_name, tool_func in module_tools.items():
                    self.tool_registry.register_tool(tool_name, tool_func)
                    func.log(f"Registered tool '{tool_name}' from module '{module_name}'.")

    def _format_recent_outcomes(self, outcomes: list, length=3000) -> list:
        """
        Formats raw tool execution results into a readable list for the LLM context.

        Args:
            outcomes: A list of tool result records.
            length: The maximum character length for the result string before truncation.

        Returns:
            A list of dictionaries, each containing the tool name and its JSON-serialized result.
        """
        formatted = []
        for o in outcomes:
            raw_str = json.dumps(o["result"])
            # TODO: Consider more intelligent truncation that preserves JSON structure or key info instead of naive character cut-off
            # final_res = (raw_str[:length] + "... [TRUNCATED]") if len(raw_str) > length else raw_str
            formatted.append({"tool": o["tool"], "result": raw_str})
        return formatted


    def _handle_format_error(self, agent: str, error: str) -> bool:
        """
        Handles repeated parsing failures, enforcing a limit to prevent infinite loops.

        Args:
            agent: The agent that failed to produce valid output.
            error: The error message received from the LLM connector.

        Returns:
            True if the loop should continue (after injecting an error message), False if the loop must halt.
        """
        self.format_error_count += 1
        
        if self.format_error_count >= 3:
            self.emit(AgentEventType.HEADER, agent, "Sentinel loop error!", subtitle=f"{agent} stuck in format loop.")
            # In a non-interactive test environment, we can't ask for input.
            # We will log the error and break the loop.
            self.emit(AgentEventType.ERROR, agent, f"Agent {agent} failed to produce valid output 3 times. Halting loop.")
            return False

        self.emit(AgentEventType.INFO, agent, f"Malformed response from {agent}, retrying ({self.format_error_count}/3)", status="WARN")

        error_msg = (
            f"PARSING FAILURE: {error}. "
            "Your previous output contained invalid structure. "
            "You must discard that attempt and rewrite your response. "
        )
        self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": error_msg})
        return True

    def _gatekeeper(self, tool: str, params: Dict[str, Any], agent: Optional[str] = None) -> bool:
        """
        Acts as an authorization gatekeeper for tool execution, prompting the user if necessary.

        Args:
            tool: The name of the tool being called.
            params: The parameters associated with the tool call.
            agent: The agent requesting the tool.

        Returns:
            True if the tool is authorized to run, False otherwise.
        """
        if self.cancel_event.is_set():
            return False  # turn was interrupted: never prompt or run anything more

        if tool in self.auto_authorized_tools or tool not in get_hil_tools():
            self.emit(AgentEventType.TOOL_CALL, agent, tool=tool, params=params, gated=False)
            return True

        choice = self.io.request_permission(tool, params)

        # TODO: Improve the mechanism to remember user choices for specific tools or paths to avoid repeated prompts in the same session.
        if choice == PERMISSION_ALWAYS:
            self.auto_authorized_tools.add(tool)
        if choice in (PERMISSION_ALWAYS, PERMISSION_YES):
            self.emit(AgentEventType.TOOL_CALL, agent, tool=tool, params=params, gated=True)
            return True
        return False

    @staticmethod
    def _targets_for_prompt(agent: str, config: Dict[str, Any]) -> List[str]:
        """The agent's allowed targets as it sees them: its own name is shown as SELF, listed first."""
        allowed = config.get("allowed_targets", [STOP_SIGNAL, USER_TARGET])
        others = [t for t in allowed if str(t).strip().upper() not in (agent, SELF_TARGET)]
        return [SELF_TARGET] + others

    @staticmethod
    def _resolve_target_alias(target: str, agent: str) -> str:
        """Maps SELF to the agent that produced the response (e.g. ENGINEER -> SELF -> ENGINEER)."""
        return agent if target == SELF_TARGET else target

    def _validate_target(self, target: str, is_empty: bool, agent: str, config: Dict[str, Any]) -> str:
        """
        Validates the intended transition target specified in the LLM response.

        Args:
            target: The target agent name from the LLM response.
            is_empty: Boolean indicating if the action/target field was empty.
            agent: The current agent.
            config: The current agent's configuration.

        Returns:
            The validated target agent name, or the current agent if validation fails or no transition is specified.
        """
        if target == USER_TARGET: return USER_TARGET
        allowed = config.get("allowed_targets", [STOP_SIGNAL, "USER"])
        # An agent may always stay on itself (SELF resolves to it), even if not listed.
        if target and target != agent and target not in allowed:
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"Invalid transition target: {target}"})
            return agent
        if is_empty and not target:
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": "Instruction: Call a tool or transition."})
            return agent
        return target