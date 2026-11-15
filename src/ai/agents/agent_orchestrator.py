import os
import re
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
from ai.agents.memory_manager import AgentMemory, MemoryManager
from ai.agents.context_sentinel import ContextSentinel
from ai.agents.context_enricher import ContextEnricher, FILE_TOOLS_WRITE, paths_from_params
from ai.agents.payload_limits import DEFAULT_TOOL_RESULT_MAX_CHARS, cap_tool_result
from ai.agents.tool_catalog import OPEN_TOOLS, ToolCatalog
from ai.agents.session_manager import AgentSessionManager
from ai.core.events import Events
from ai.services.directory_manager import DirectoryManager
from ai.services.module_registry import ModuleRegistry
from ai.modules.knowledge.sources import agent_allowed_sources
from ai.services.process_manager import ProcessManager
from ai.tools.mcp_bridge import MCPBridge
from ai.tools.mcp_admin_tools import ALWAYS_GATED as MCP_ALWAYS_GATED
from ai.agents import approval_scope

# MCP admin tools given to every agent; enabling a server always needs the user's approval.
MCP_ADMIN_TOOLS = ("list_mcp_servers", "enable_mcp_server")
ALWAYS_GATED_TOOLS = tuple(MCP_ALWAYS_GATED)
from ai.tools.tool_registry import ToolRegistry
from ai.tools.category import ToolCategory, ToolCategoryError

MAX_ITERATIONS = 300  # same as the shipped pipelines
MANAGER_AGENT_ROLE = "management"

STOP_SIGNAL = "STOP"
MASTER_AGENT = "MASTER"
USER_TARGET = "USER"
# Alias any agent may target to mean "itself"; resolved to the acting agent's name.
SELF_TARGET = "SELF"
DONE_SIGNAL = "DONE"

# Turns an agent may end with no tool and itself as target before control is handed to the user.
MAX_IDLE_SELF_TURNS = 1
# Identical tool calls (same tool + parameters) within the last 5 that stop the run.
STAGNATION_STOP = 5

# Fallback list of tools that require explicit user authorization (HIL).
# The effective list comes from the HIL_TOOLS setting in config.json.
GATED_TOOLS = ["execute_command"]


_WRAPPER_TAG_RE = re.compile(r"</?response_to_user\s*>|<!?\[?CDATA\[|\]\]>", re.IGNORECASE)


def _strip_wrapper_tags(text: Any) -> str:
    """Small models sometimes repeat the <response_to_user> tags (or a CDATA wrapper) inside the field."""
    return _WRAPPER_TAG_RE.sub("", str(text or "")).strip()


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
    # Set when a one-shot run stops before a tool that needs approval (see oneshot_hil_tools).
    _approval_stop: Optional[tuple] = None

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
        self._idle_turns: Dict[str, int] = {}
        self._turn_changed: List[str] = []  # files written in the current turn (knowledge auto-update)

        self.context_sentinel = ContextSentinel(
            self.llm_connector, 
            threshold=0.9, 
            max_tokens=self.llm_connector.get_context_limit(),
            buffer=self.llm_connector.get_max_tokens()
        )

        self.mcp_bridge = MCPBridge(self.tool_registry)
        # Load external servers from config
        directory = DirectoryManager()
        # system config first, then the user's: user servers are added or override by name
        from ai.tools.mcp_config import config_paths
        self.mcp_bridge.load_from_configs(config_paths(directory))
        # list_mcp_servers / enable_mcp_server: every agent gets them (enabling always asks the user)
        from ai.tools.mcp_admin_tools import MCPAdminTools
        try:
            self.tool_registry.register_category(MCPAdminTools(self.mcp_bridge))
        except Exception as e:
            func.log(f"[MCP] admin tools unavailable: {e}", level="WARN")
        
        # Memory State
        self.memory = MemoryManager(list(self.agents.keys()))
        self.vector_memory = None
        self.knowledge = None  # KnowledgeStore, when the knowledge module is loaded
        self.context_enricher: Optional[ContextEnricher] = None
        
        # Session State (Initialized in run_loop)
        self.session_manager = None
        self.session_id = None

    def emit(self, event_type: AgentEventType, agent: Optional[str] = None, text: str = "", **data):
        """Shortcut to send an event through the I/O channel."""
        if event_type == AgentEventType.STATUS:
            self._publish_activity(agent, text, data)
        self.io.emit(AgentEvent(type=event_type, agent=agent, text=text, data=data))

    def _publish_activity(self, agent: Optional[str], text: str, data: dict) -> None:
        """Mirrors the STATUS line into the process registry as ``[n/max] agent: status``."""
        if "iteration" in data:
            self._activity_progress = f"[{data['iteration']}/{data.get('max_iterations', '?')}] "
        progress = getattr(self, "_activity_progress", "")
        ProcessManager.set_state("activity", f"{progress}{agent or 'agent'}: {text}".strip())

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
        self._approval_stop: Optional[tuple] = None
        self._last_message = ""
        self._idle_turns: Dict[str, int] = {}
        self._turn_changed = []
        self.session_id = session_id
        self._turn_prompt = user_prompt
        self.session_manager = AgentSessionManager(session_id)
        self._initialize_modules()

        start_iteration, current_agent = self._get_saved_session(session_id=session_id, user_prompt=user_prompt)

        max_iterations = self.pipeline_config.get("max_iterations", MAX_ITERATIONS)
        end_iteration = start_iteration + max_iterations
        executed = 0

        for i in range(start_iteration, end_iteration):
            if self.cancel_event.is_set():
                return self._finish("cancelled", current_agent, executed)

            # Agent state validation at the start of the loop
            if current_agent in [None, STOP_SIGNAL]:
                self.emit(AgentEventType.INFO, text="Pipeline execution finished.", status="SUCCESS")
                return self._finish("done", current_agent, executed)

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
            agent_config["name"] = current_agent
            agent_config["tool_descriptions"] = self._tool_descriptions(active_tools, agent_mem)
            if self._uses_categories(active_tools):
                agent_config["tools"].append(OPEN_TOOLS)

            payload = self._prepare_payload(user_prompt, current_agent)
            payload, was_compressed = self.context_sentinel.enforce_limits(
                current_agent, self.memory, payload, vector_memory=self.vector_memory,
                overhead_chars=self._prompt_overhead(agent_config),
                keep_recent_results=self.KEEP_RECENT_RESULTS,
            )
            if was_compressed:
                # the Sentinel puts the memory lists back into the payload: cut them again
                payload["messages_received"] = self._capped_messages(payload.get("messages_received") or [])
                payload["conversation_history"] = self._capped_history(payload.get("conversation_history") or [],
                                                                       payload.get("messages_received") or [])

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
                hint = "\nSession saved: send a message (e.g. 'continue') to retry." if response.get("transient") else ""
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
                next_agent = self.pipeline_config.get("entry_point", MASTER_AGENT)

            current_agent = next_agent

        if current_agent in [None, STOP_SIGNAL]:
            self.emit(AgentEventType.INFO, text="Pipeline execution finished.", status="SUCCESS")
            return self._finish("done", current_agent, executed)

        self.emit(AgentEventType.ERROR, current_agent, f"Iteration budget exhausted ({max_iterations}).")
        return self._finish("max_iterations", current_agent, executed)

    def _finish(self, reason: str, agent: Optional[str], executed: int, message: Optional[str] = None) -> TurnResult:
        """Builds the TurnResult returned by run_loop."""
        ProcessManager.set_state("activity", f"agent {reason}" + (f" ({agent})" if agent and agent != STOP_SIGNAL else ""))
        self._activity_progress = ""
        if executed > 0 and reason in ("done", "awaiting_user", "max_iterations"):
            self._record_episode(reason, self._last_message if message is None else message)
        if reason in ("done", "awaiting_user"):
            self._auto_update_knowledge()
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
            allowed.extend(MCP_ADMIN_TOOLS)
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

    def _categories_enabled(self) -> bool:
        return bool(self._setting(self._current_config(), ProgramSetting.AGENT_TOOL_CATEGORIES, True))

    def _uses_categories(self, active_tools: Dict[str, Callable]) -> bool:
        """True when the agent sees categories (setting on and at least one of its tools has one)."""
        if not self._categories_enabled():
            return False
        catalog = ToolCatalog(self.tool_registry)
        return any(catalog.category_for(name) for name in active_tools)

    def _tool_descriptions(self, active_tools: Dict[str, Callable], agent_mem: AgentMemory) -> str:
        """The AVAILABLE TOOLS text: every tool in full, or categories with only the open ones in full."""
        if not self._uses_categories(active_tools):
            return "\n".join(self.tool_registry.get_tool_info(name) for name in active_tools)
        return ToolCatalog(self.tool_registry).describe(active_tools, agent_mem.open_categories)

    def _open_tools(self, agent: str, params: Dict[str, Any]) -> bool:
        """Runs open_tools: unlocks the requested categories for this agent."""
        mem = self.memory.get_agent_memory(agent)
        result = ToolCatalog(self.tool_registry).open(params, self._assemble_agent_tools(agent), mem.open_categories)
        self.memory.record_tool_result(agent, OPEN_TOOLS, params, result)
        self.emit(AgentEventType.TOOL_RESULT, agent, tool=OPEN_TOOLS, params=params, result=result)
        return result.get("status") == "SUCCESS"

    def _open_category_of(self, agent: str, tool_name: str) -> None:
        """A tool of a closed category was called directly: it runs, and its category opens."""
        category = ToolCatalog(self.tool_registry).category_for(tool_name)
        mem = self.memory.get_agent_memory(agent)
        if category and mem is not None and category not in mem.open_categories:
            mem.open_categories.append(category)

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
            "objective": user_prompt if is_mgr else self._labor_objective(mem),
            "agent_notes": mem.notes,
            "messages_received": self._capped_messages(mem.messages_received),
            "conversation_history": self._capped_history(mem.history[-10:], mem.messages_received),
            "recent_outcomes": self._format_recent_outcomes(self.memory.context.tool_results[-3:]),
            "context": {"files_in_project": list(set(filter(None, known_files)))}
        }
        
        allowed_sources = agent_allowed_sources(self.agents.get(agent))
        if self.knowledge is not None:
            self.knowledge.tools.set_scope(allowed_sources)
        if self.context_enricher is not None:
            self.context_enricher.enrich(
                payload, agent, mem.current_task or user_prompt,
                tool_results=self.memory.context.tool_results[-10:],
                allowed_sources=allowed_sources,
            )
        return payload

    # Tool results in conversation_history were already seen in an earlier step: a short reminder is
    # enough, except for the most recent ones (the agent is usually still working with them).
    HISTORY_RESULT_MAX_CHARS = 1500
    KEEP_RECENT_RESULTS = 2

    def _capped_history(self, history: List[Dict[str, Any]], current: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        History for the payload: the latest tool results (KEEP_RECENT_RESULTS minus the ones of this
        turn) keep the normal size limit, older ones become short reminders.
        """
        in_turn = sum(1 for m in current if isinstance(m, dict) and "result" in m)
        still_needed = max(0, self.KEEP_RECENT_RESULTS - in_turn)
        result_idx = [i for i, m in enumerate(history) if isinstance(m, dict) and "result" in m]
        recent = set(result_idx[-still_needed:]) if still_needed else set()
        full = self._capped_messages([history[i] for i in sorted(recent)])
        full_by_idx = dict(zip(sorted(recent), full))
        short = self._capped_messages(history, self.HISTORY_RESULT_MAX_CHARS)
        return [full_by_idx.get(i, short[i]) for i in range(len(history))]

    def _capped_messages(self, messages: List[Dict[str, Any]], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Messages for the payload, with oversized tool results cut (memory keeps them whole)."""
        if limit is not None:
            return [({**m, "result": cap_tool_result(m["result"], limit)} if isinstance(m, dict) and "result" in m else m)
                    for m in messages]
        limit = self._int_setting(self._current_config(), ProgramSetting.AGENT_TOOL_RESULT_MAX_CHARS,
                                  DEFAULT_TOOL_RESULT_MAX_CHARS)
        if limit > 0:
            # never more than a quarter of the prompt room of the current model (~3.2 chars/token)
            try:
                window, reserve = self.context_sentinel.current_limits()
                if window > reserve:
                    limit = min(limit, max(2000, int((window - reserve) * 3.2 * 0.25)))
            except Exception:
                pass
        out = []
        for msg in messages:
            if isinstance(msg, dict) and "result" in msg:
                capped = cap_tool_result(msg["result"], limit)
                out.append(msg if capped is msg["result"] else {**msg, "result": capped})
            else:
                out.append(msg)
        return out

    def _prompt_overhead(self, agent_config: Dict[str, Any]) -> int:
        """Characters sent besides the payload: the agent's prompt file, output rules and tool descriptions."""
        cache = self.__dict__.setdefault("_prompt_sizes", {})
        size = len(agent_config.get("tool_descriptions") or "")
        paths = [agent_config.get("prompt_file_path")]
        try:
            paths.append(os.path.join(DirectoryManager().get_system_dir(), "inject", "agent-out.md"))
        except Exception:
            pass
        for path in paths:
            if not path:
                continue
            if path not in cache:
                try:
                    cache[path] = os.path.getsize(path)
                except OSError:
                    cache[path] = 0
            size += cache[path]
        return size

    @staticmethod
    def _labor_objective(mem: AgentMemory) -> str:
        """
        The task a non-manager agent is working on: the last message it received from an agent or
        the user (kept across turns in current_task; tool results never replace it).
        """
        for msg in reversed(mem.messages_received):
            if msg.get("from") != "SYSTEM" and (msg.get("message") or msg.get("task")):
                return msg.get("message") or msg.get("task")
        current = str(mem.current_task or "").strip()
        if current and current != "Waiting for tasks...":
            return current
        return "Continue."

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

        msg = _strip_wrapper_tags(response.get("response_to_user", ""))
        if msg:
            # The same answer repeated on a later step is not shown again.
            if msg.strip() != (self._last_message or "").strip():
                # Said alongside a tool call: progress narration, not an answer to the user.
                has_tool = bool(tool_name) and str(tool_name).upper() != "NULL"
                self.emit(AgentEventType.MESSAGE, agent, msg, narration=has_tool and target != USER_TARGET)
            self._last_message = msg

        self.memory.update_agent_history_and_notes(agent, response)

        # Small models sometimes put an agent's name in tool_name to delegate: treat it as the target.
        named = str(tool_name or "").strip().upper()
        if named and named in self.agents and tool_name not in config.get("tools", []):
            if not target or target == agent:
                target = named
            tool_name, params = None, {}

        is_empty = not tool_name or str(tool_name).upper() == "NULL"

        if target == USER_TARGET:
            self._idle_turns.pop(agent, None)
            return self._hand_to_user(agent, action, msg, config, tool_name=None if is_empty else tool_name, params=params)

        if not is_empty:
            self._idle_turns.pop(agent, None)
            if self.memory.check_stagnation(tool_name, params):
                repeats = self.memory.context.repeat_count
                if repeats >= STAGNATION_STOP:
                    note = (f"Stopped: {agent} called {tool_name} with the same parameters {repeats} times "
                            f"in a row without progress.")
                    self.emit(AgentEventType.ERROR, agent, note)
                    return self._hand_to_user(agent, {}, msg or note, config)
                self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": (
                    f"You called {tool_name} with the same parameters {repeats} times in your last steps; "
                    "the result will not change. Use the result you already have, try a different approach, "
                    "or report to USER.")})
        elif not target or target == agent:
            return self._handle_idle_turn(agent, msg, config)

        validated_target = self._validate_target(target, is_empty, agent, config)

        if not is_empty and validated_target != STOP_SIGNAL:
            if not self._handle_tool_execution(tool_name, params, agent, config):
                return agent

        msg_to_target = action.get("message_to_target") or action.get("task_for_target")
        if validated_target and validated_target not in [STOP_SIGNAL, agent, USER_TARGET]:
            if not msg_to_target:
                # Delegated without a task: pass on what the delegating agent is working on,
                # so the other agent does not start from nothing.
                own = self.memory.get_agent_memory(agent)
                parts = [p for p in (getattr(own, "current_task", None), msg) if p]
                msg_to_target = "\n\n".join(parts) or "Continue the current task."
            self.memory.add_message_to_agent(validated_target, {"from": agent, "message": msg_to_target, "task": action.get("task_for_target", "")})

        return validated_target or agent

    def _hand_to_user(self, agent: str, action: Dict[str, Any], msg: str, config: Dict[str, Any],
                      tool_name: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Gives control back to the user: asks the question (or delivers the answer) and either waits
        for the reply (blocking UIs) or ends the turn (the next user message is the reply).
        """
        # A tool call in the same response must still run before handing back to the user
        # (it used to be silently skipped while the agent reported it as done).
        if tool_name:
            self._handle_tool_execution(tool_name, params or {}, agent, config)
            if self._approval_stop is not None:
                return agent  # stopped for approval: that note is what the user needs to see
        question = action.get("message_to_target")
        prompt = question or msg or "Clarification required."
        # If the agent only handed control back after answering, its response was
        # already shown; don't print a generic question on top of it.
        if question or not msg:
            self.emit(AgentEventType.QUESTION, agent, prompt)
        reply = self.io.request_user_input(agent, prompt).strip() if self.io.blocking_user_input else ""
        if reply:
            self.memory.add_message_to_agent(agent, {"from": "USER", "message": reply, "task": reply})
        else:
            # Non-blocking UIs, or no reply: end the turn; the next user message is the reply.
            self._awaiting_user = prompt
        return agent

    def _handle_idle_turn(self, agent: str, msg: str, config: Dict[str, Any]) -> str:
        """
        A response with no tool whose target is the agent itself does no work. The first time the
        agent is told how to end its turn; if it does it again, its answer is handed to the user.
        """
        count = self._idle_turns.get(agent, 0) + 1
        self._idle_turns[agent] = count
        if count > MAX_IDLE_SELF_TURNS:
            self._idle_turns.pop(agent, None)
            func.log(f"{agent} ended {count} turns without a tool and targeting itself; handing control to the user.")
            return self._hand_to_user(agent, {}, msg or self._last_message, config)

        if msg:
            hint = ("You answered in response_to_user but called no tool and targeted yourself, so the turn did not end. "
                    "If the task is done, end with agent_target USER (or STOP, or the agent that gave you the task). "
                    "Otherwise call a tool. Do not repeat the answer.")
        else:
            hint = "You called no tool and targeted yourself. Call a tool, or target USER, STOP or another agent to end your turn."
        self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": hint})
        return agent

    def _handle_tool_execution(self, tool_name: str, params: Dict[str, Any], agent: str, config: Dict[str, Any]) -> bool:
        """
        Executes a tool, handling authorization checks.

        Args:
            tool_name: The name of the tool to execute.
            params: The parameters passed to the tool.
            agent: The agent attempting to use the tool.
            config: The agent's configuration.

        Returns:
            True if the tool executed successfully, False otherwise.
        """
        if OPEN_TOOLS in config.get("tools", []):
            if tool_name == OPEN_TOOLS:
                return self._open_tools(agent, params if isinstance(params, dict) else {})
            if tool_name not in config.get("tools", []) and \
                    str(tool_name).strip().lower() in ToolCatalog(self.tool_registry).group(config["tools"])[0]:
                # a category name used as a tool: small models do this, it means "open it"
                return self._open_tools(agent, {"category": str(tool_name).strip().lower()})

        if tool_name not in config.get("tools", []):
            self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": f"Unauthorized tool: {tool_name}"})
            func.debug(f"Agent {agent} attempted to use unauthorized tool: {tool_name} , allowed tools: {config.get('tools', [])}", level="WARN")
            self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                      result={"status": "UNAUTHORIZED", "error": f"'{tool_name}' is not allowed for {agent}"})
            return False

        self._approval_stop = None
        if not self._gatekeeper(tool_name, params, agent):
            if self._approval_stop is not None:
                note = (f"Stopped before running {tool_name}: in one-shot mode it needs the user's approval "
                        f"(oneshot_hil_tools in the pipeline). Resume the session interactively to approve it.")
                self.memory.add_message_to_agent(agent, {"from": "SYSTEM", "message": (
                    f"{tool_name} did not run: the run stopped to wait for the user's approval. "
                    f"When the user resumes, call it again if it is still needed.")})
                self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                          result={"status": "NEEDS_APPROVAL", "error": "waiting for the user's approval"})
                self.emit(AgentEventType.INFO, agent, note)
                self._awaiting_user = note
                return False
            self.memory.add_message_to_agent(agent, {"from": "USER", "message": "Access Denied."})
            self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                      result={"status": "DENIED", "error": "User denied execution."})
            return False

        self._open_category_of(agent, tool_name)
        result = self.tool_registry.execute_tool(tool_name, params)
        self.memory.record_tool_result(agent, tool_name, params, result)
        self._mark_knowledge_stale(tool_name, params, result)
        if tool_name in ("update_knowledge", "ingest_knowledge") and isinstance(result, dict) \
                and result.get("status") in ("SUCCESS", "PARTIAL"):
            self._register_knowledge_query_tools()   # new knowledge is usable in the next step
            if self.context_enricher is not None:
                self.context_enricher.invalidate()
        self.emit(AgentEventType.TOOL_RESULT, agent, tool=tool_name, params=params,
                  result=result if isinstance(result, dict) else {"status": "SUCCESS", "result": result})
        return True

    def _initialize_modules(self):
        """
        Initializes all registered modules, centralizing their tools in the ToolRegistry.

        Long-term memory is opened for the current scope (LTM_SCOPE: the workspace by default),
        knowledge gets the pipeline's sources, and the ContextEnricher is (re)built over both.
        """
        config = self._current_config()
        self.vector_memory = None
        self.knowledge = None

        for module_name, mod in self.module_registry.items():
            if not mod:
                continue

            if module_name == "vector_memory":
                self._initialize_ltm(mod, config)
                instance = self.vector_memory
            elif module_name == "knowledge":
                self._initialize_knowledge(mod)
                continue  # tools registered there, only when sources exist
            else:
                instance = mod.get_instance()

            provider = mod if isinstance(mod, ToolCategory) else getattr(instance, "tools", None) if instance else None
            if provider is not None:
                self._register_tool_provider(module_name, provider)

        self.context_enricher = ContextEnricher(
            knowledge=self.knowledge,
            ltm=self.vector_memory,
            knowledge_top_k=self._int_setting(config, ProgramSetting.KNOWLEDGE_INJECT_TOP_K, 4),
            max_chars=self._int_setting(config, ProgramSetting.KNOWLEDGE_INJECT_MAX_CHARS, 1500),
            ltm_top_k=self._int_setting(config, ProgramSetting.LTM_INJECT_TOP_K, 4),
            ltm_min_relevance=float(self._setting(config, ProgramSetting.LTM_MIN_RELEVANCE, 0.3) or 0.3),
        )

    @staticmethod
    def _current_config() -> Any:
        try:
            return ProgramConfig.get_current()
        except Exception:
            return None

    @staticmethod
    def _setting(config: Any, key: ProgramSetting, default: Any) -> Any:
        try:
            value = config.get(key, default) if config is not None else default
        except Exception:
            value = default
        return default if value is None else value

    @classmethod
    def _int_setting(cls, config: Any, key: ProgramSetting, default: int) -> int:
        try:
            return int(cls._setting(config, key, default))
        except (TypeError, ValueError):
            return default

    def _initialize_ltm(self, mod: Any, config: Any) -> None:
        """Opens long-term memory for this session's scope (see resolve_ltm_scope)."""
        try:
            from ai.modules.vector_memory.vector_memory import resolve_ltm_scope
            from ai.tools.base import get_project_root
            scope = resolve_ltm_scope(self._setting(config, ProgramSetting.LTM_SCOPE, "project"),
                                      self.session_id or "default", get_project_root())
            mod.initialize(self.session_id or "default", getattr(self.llm_connector, "llm", None), scope_key=scope)
            self.vector_memory = mod.get_instance()
        except Exception as e:
            func.error(f"VectorMemory initialization failed: {e}")
            self.vector_memory = None
        func.log(f"VectorMemory: {'CONNECTED' if self.vector_memory else 'DISABLED'}")

    def _initialize_knowledge(self, mod: Any) -> None:
        """
        Loads the knowledge registered for this project and the pipeline's sources, and registers
        the knowledge tools: build tools always, query tools when at least one source is loaded.
        """
        try:
            from ai.tools.base import get_project_root
            root = get_project_root()
            if hasattr(mod, "ensure_project"):
                mod.ensure_project(root)
            pipeline_sources = self.pipeline_config.get("knowledge")
            if pipeline_sources and hasattr(mod, "add_sources"):
                mod.add_sources(pipeline_sources if isinstance(pipeline_sources, list) else [pipeline_sources],
                                base_dir=root, remember=False)
            store = mod.get_instance()
        except Exception as e:
            func.error(f"Knowledge initialization failed: {e}")
            return
        if store is None:
            return
        self.knowledge = store
        store.tools.set_llm(getattr(self.llm_connector, "llm", None))
        self._register_knowledge_query_tools()

    def _register_tool_provider(self, module_name: str, provider: Any) -> None:
        """Registers a module's tools: as a category when it is a ToolCategory, else one by one."""
        if isinstance(provider, ToolCategory) and hasattr(self.tool_registry, "register_category"):
            try:
                tools = self.tool_registry.register_category(provider)
                func.log(f"Registered tool category '{provider.name}' ({', '.join(tools)}) from module '{module_name}'.")
            except ToolCategoryError as e:
                func.error(f"Tools of module '{module_name}' not registered: {e}")
            return
        get_tools = getattr(provider, "get_tools", None)
        if not callable(get_tools):
            return
        for tool_name, tool_func in get_tools().items():
            self.tool_registry.register_tool(tool_name, tool_func)
            func.log(f"Registered tool '{tool_name}' from module '{module_name}'.")

    def _register_knowledge_query_tools(self) -> None:
        """(Re)registers the knowledge tools: build tools always, query tools once a source is loaded."""
        store = self.knowledge
        if store is None:
            return
        tools = store.tools
        if isinstance(tools, ToolCategory) and hasattr(self.tool_registry, "register_category"):
            self._register_tool_provider("knowledge", tools)
        else:
            found = dict(tools.get_build_tools()) if hasattr(tools, "get_build_tools") else {}
            if store.has_sources():
                found.update(tools.get_tools())
            for tool_name, tool_func in found.items():
                self.tool_registry.register_tool(tool_name, tool_func)
        if store.has_sources():
            func.log(f"Knowledge: {store.stats()}")

    def _mark_knowledge_stale(self, tool_name: str, params: Dict[str, Any], result: Any) -> None:
        """Flags knowledge of files the agent changed, so it is shown as possibly outdated."""
        if tool_name not in FILE_TOOLS_WRITE:
            return
        if isinstance(result, dict) and str(result.get("status", "")).upper() not in ("SUCCESS", "OK"):
            return
        for path in paths_from_params(params):
            if path not in self._turn_changed:
                self._turn_changed.append(path)
        if self.knowledge is None:
            return
        changed = False
        for path in paths_from_params(params):
            changed = self.knowledge.mark_stale(path) or changed
        if changed and self.context_enricher is not None:
            self.context_enricher.invalidate()

    def _auto_update_knowledge(self) -> None:
        """
        Regenerates the knowledge of the files changed in this turn, when the project's knowledge
        was built by the app (KNOWLEDGE_AUTO_UPDATE, at most KNOWLEDGE_AUTO_UPDATE_MAX files).
        """
        files, self._turn_changed = list(self._turn_changed), []
        store = self.knowledge
        service = getattr(store, "service", None) if store is not None else None
        if not files or service is None:
            return
        config = self._current_config()
        if not self._setting(config, ProgramSetting.KNOWLEDGE_AUTO_UPDATE, True):
            return
        try:
            from ai.tools.base import get_project_root
            root = get_project_root()
            if not service.registry.build_config(root).get("output"):
                return  # knowledge not generated by the app for this project: nothing to keep in sync
            limit = self._int_setting(config, ProgramSetting.KNOWLEDGE_AUTO_UPDATE_MAX, 5)
            if limit <= 0:
                return
            self.emit(AgentEventType.INFO, text=f"Updating project knowledge for {min(len(files), limit)} changed file(s)...", status="INFO")
            report = service.build(root, llm=getattr(self.llm_connector, "llm", None), files=files, max_files=limit)
            if report["done"] or report["failed"]:
                text = f"Knowledge updated: {len(report['done'])} file(s)"
                if report["failed"]:
                    text += f", {len(report['failed'])} failed"
                self.emit(AgentEventType.INFO, text=text, status="SUCCESS" if not report["failed"] else "WARN")
                if self.context_enricher is not None:
                    self.context_enricher.invalidate()
        except Exception as e:
            func.debug(f"Knowledge auto-update failed: {e}")

    def _record_episode(self, reason: str, message: str) -> None:
        """
        Stores what this turn was about and how it ended as an 'episode' memory (no LLM call),
        and consolidates memory with a reflection once enough new memories piled up.
        """
        ltm = self.vector_memory
        if ltm is None:
            return
        task = (getattr(self, "_turn_prompt", "") or "").strip()
        if not task:
            return
        try:
            changed = []
            for res in self.memory.context.tool_results:
                if res.get("tool") in ("write_file", "patch_file", "delete_file") and \
                        isinstance(res.get("result"), dict) and res["result"].get("status") == "SUCCESS":
                    for p in paths_from_params(res.get("parameters") or {}):
                        if p not in changed:
                            changed.append(p)
            parts = [f"Task: {task[:500]}", f"Outcome ({reason}): {(message or '').strip()[:700] or 'no message'}"]
            if changed:
                parts.append("Files changed: " + ", ".join(changed[:15]))
            ltm.add_memory("\n".join(parts), source=f"EPISODE_{self.session_id or ''}", memory_type="episode")
        except Exception as e:
            func.debug(f"Could not record episode: {e}")
            return

        threshold = self._int_setting(self._current_config(), ProgramSetting.LTM_AUTO_REFLECT_MIN, 15)
        if reason == "done" and threshold > 0 and getattr(ltm, "new_memories", 0) >= threshold:
            try:
                self.emit(AgentEventType.INFO, text="Consolidating long-term memory...", status="INFO")
                ltm.trigger_reflection()
            except Exception as e:
                func.debug(f"Auto reflection failed: {e}")

    def _format_recent_outcomes(self, outcomes: list, length=1500) -> list:
        """
        Formats the last tool results for the LLM context: a short reminder of what was done
        (the full results reach the agent once, in messages_received).

        Args:
            outcomes: A list of tool result records.
            length: The maximum character length of each result (cut keeping its structure).

        Returns:
            A list of dictionaries, each containing the tool name and its JSON-serialized result.
        """
        formatted = []
        for o in outcomes:
            result = cap_tool_result(o.get("result"), length)
            formatted.append({"tool": o.get("tool"), "result": json.dumps(result, default=str)})
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

        bridge = getattr(self, "mcp_bridge", None)
        oneshot_tools = self._oneshot_hil_tools()
        gated = oneshot_tools if oneshot_tools is not None else get_hil_tools()
        needs_approval = (tool in gated or tool in ALWAYS_GATED_TOOLS
                          or bool(bridge is not None and bridge.requires_approval(tool)))
        always_asks = tool in ALWAYS_GATED_TOOLS
        if not needs_approval or (not always_asks and approval_scope.is_allowed(tool, params, self.auto_authorized_tools)):
            self.emit(AgentEventType.TOOL_CALL, agent, tool=tool, params=params, gated=False)
            return True

        if oneshot_tools is not None and getattr(self.io, "can_ask_permission", True) is False:
            # One-shot with nobody to ask: stop here instead of denying and letting the agent carry on.
            self._approval_stop = (tool, params)
            return False

        choice = self.io.request_permission(tool, params)

        # "always" covers this command / folder, not the whole tool (see approval_scope)
        if choice == PERMISSION_ALWAYS:
            rule = approval_scope.rule_for(tool, params, never_remember=ALWAYS_GATED_TOOLS)
            if rule:
                self.auto_authorized_tools.add(rule)
        if choice in (PERMISSION_ALWAYS, PERMISSION_YES):
            self.emit(AgentEventType.TOOL_CALL, agent, tool=tool, params=params, gated=True)
            return True
        return False

    def _oneshot_hil_tools(self) -> Optional[List[str]]:
        """The pipeline's ``oneshot_hil_tools`` during a one-shot run, else None (use HIL_TOOLS)."""
        if getattr(self.io, "one_shot", False) is not True:
            return None
        tools = (getattr(self, "pipeline_config", None) or {}).get("oneshot_hil_tools")
        return list(tools) if isinstance(tools, (list, tuple)) else None

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