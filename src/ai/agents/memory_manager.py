import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

@dataclass
class AgentMemory:
    """Stores the internal state and history of a single agent.

    Attributes:
        notes: The agent's running notes or summary of its state.
        messages_received: A list of messages recently received by the agent.
        history: A chronological log of the agent's past interactions and thoughts.
        current_task: The current objective or state of the agent.
        manifest: A dictionary containing structured metadata about the agent's state.
    """
    notes: str = "System initialized."
    messages_received: list = field(default_factory=list)
    history: list = field(default_factory=list)
    current_task: str = "Waiting for tasks..."
    manifest: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestratorContext:
    """Stores the global context for the orchestration pipeline.

    Attributes:
        tool_results: A list of all recorded results from executed tools.
        task: The primary task assigned to the orchestrator.
        plan: The sequence of steps or actions planned for the overall process.
        current_step_index: The index of the step currently being executed in the plan.
        action_history_fp: A history of recent tool call fingerprints to detect loops.
        repeat_count: A counter indicating how many times the current action has been repeated.
    """
    tool_results: list = field(default_factory=list)
    task: str = ""
    plan: list = field(default_factory=list)
    current_step_index: int = 1
    action_history_fp: list = field(default_factory=list)
    repeat_count: int = 0

class MemoryManager:
    """Manages the state of the orchestrator and all agents with persistence support.

    This class centralizes the state management for the entire AI system, allowing
    for serialization, loading, and interaction tracking across multiple agents.
    """

    def __init__(self, agent_names: List[str]):
        """
        Initializes the MemoryManager.

        Args:
            agent_names: A list of names for the agents that the manager should track.
        """
        self.context = OrchestratorContext()
        self.agents: Dict[str, AgentMemory] = {
            name: AgentMemory() for name in agent_names
        }

    def serialize(self) -> Dict[str, Any]:
        """
        Collapses the live memory state into a serializable dictionary.

        Returns:
            A dictionary containing the serialized context and agent memories.
        """
        return {
            "context": asdict(self.context),
            "agents": {name: asdict(mem) for name, mem in self.agents.items()}
        }

    def load_state(self, data: Dict[str, Any]):
        """
        Restores the memory state from a dictionary. 
        Safely maps keys to maintain compatibility if the agent pool changes.

        Args:
            data: The dictionary containing the serialized state to load.
        """
        if not data:
            return

        ctx_data = data.get("context", {})
        for key, value in ctx_data.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

        agents_data = data.get("agents", {})
        for agent_name, agent_data in agents_data.items():
            if agent_name in self.agents:
                for key, value in agent_data.items():
                    if hasattr(self.agents[agent_name], key):
                        setattr(self.agents[agent_name], key, value)

    def get_agent_memory(self, agent_name: str) -> Optional[AgentMemory]:
        """Retrieves the memory for a specific agent.

        Args:
            agent_name: The name of the agent whose memory is requested.

        Returns:
            The AgentMemory object if found, otherwise None.
        """
        return self.agents.get(agent_name)

    def add_message_to_agent(self, target_agent: str, message_payload: Dict[str, Any]):
        """
        Adds a message payload to a target agent's received messages queue.
        Creates the agent memory on-demand if it doesn't exist.

        Args:
            target_agent: The name of the agent receiving the message.
            message_payload: The dictionary containing the message content.
        """
        agent_memory = self.agents.setdefault(target_agent, AgentMemory())
        agent_memory.messages_received.append(message_payload)

    def record_tool_result(self, agent_name: str, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]):
        """Records the result of a tool execution in the global context and for the agent.

        Args:
            agent_name: The name of the agent that executed the tool.
            tool_name: The name of the tool that was called.
            params: The parameters passed to the tool.
            result: The output dictionary returned by the tool execution.
        """
        self.context.tool_results.append({
            "agent": agent_name, 
            "tool": tool_name, 
            "parameters": params, 
            "result": result
        })
        
        if result.get("status") == "SUCCESS":
            self.context.current_step_index += 1
        
        self.add_message_to_agent(agent_name, {"from": "SYSTEM", "result": result})

    def update_agent_history_and_notes(self, agent_name: str, response: Dict[str, Any]):
        """
        Updates an agent's internal memory.
        Moves received messages to history and injects new thoughts/notes.

        Args:
            agent_name: The name of the agent whose memory is being updated.
            response: A dictionary containing the agent's latest thoughts, notes, and response.
        """
        memory = self.get_agent_memory(agent_name)
        if not memory:
            return
        memory.notes = response.get("notes", memory.notes)
        memory.manifest = response.get("manifest", {})
        
        msg_to_user = response.get("response_to_user")
        
        for m in memory.messages_received:
            memory.history.append(m)
        
        memory.history.append({
            "from": "SELF", 
            "thought": response.get("thought"), 
            "response": msg_to_user
        })
        memory.messages_received = []

    def check_stagnation(self, tool_name: Optional[str], params: Dict[str, Any]) -> bool:
        """
        Tracks identical tool calls to detect architectural loops.

        Args:
            tool_name: The name of the tool being called.
            params: The parameters used in the tool call.

        Returns:
            True if a loop condition (3 or more identical calls in the recent history) is detected, False otherwise.
        """
        current_fp = f"{tool_name}-{json.dumps(params, sort_keys=True)}"
        self.context.action_history_fp.append(current_fp)
        
        if len(self.context.action_history_fp) > 5:
            self.context.action_history_fp.pop(0)
        
        occurrences = self.context.action_history_fp.count(current_fp)
        if occurrences >= 3:
            self.context.repeat_count = occurrences
            return True
        
        self.context.repeat_count = 0
        return False
    
    def clear(self, agent: str):
        """Resets the state of a specific agent and clears the outcome context.

        Args:
            agent: The name of the agent whose state should be reset.
        """
        if agent in self.agents:
            mem = self.agents[agent]
            mem.messages_received = []
            mem.history = []
            mem.notes = "System initialized."
            mem.manifest = {}
            mem.current_task = "Waiting for tasks..."
            self.context.tool_results = []