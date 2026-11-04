## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MemoryManager** | [src/ai/agents/memory_manager.py](/src/ai/agents/memory_manager.py) |

The `MemoryManager` is a centralized state management system designed to handle the persistence and tracking of both global orchestration context and individual agent states. It provides a structured way to maintain the "memory" of the AI system, ensuring that agent thoughts, received messages, and tool execution results are preserved and can be serialized for long-term storage or session recovery.

This component acts as a critical data layer within the agentic architecture. It sits between the execution logic (such as [agent_orchestrator.md](/AgentDocs/ai/agents/agent_orchestrator.md)) and the persistence layer, providing the necessary structures (`AgentMemory` and `OrchestratorContext`) to prevent state loss during complex, multi-step reasoning tasks. It also includes logic to detect architectural loops by monitoring repetitive tool calls.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentMemory` | Class | A dataclass representing the internal state of a single agent, including notes, message history, and task status. |
| `OrchestratorContext` | Class | A dataclass storing global orchestration data, including the master plan, tool results, and loop detection fingerprints. |
| `MemoryManager` | Class | The primary controller for managing, serializing, and updating agent and orchestrator states. |
| `MemoryManager.__init__(agent_names: List[str])` | Constructor | Initializes the manager with a specific set of agent names. |
| `MemoryManager.serialize()` | Method | Returns a dictionary representation of the entire current memory state. |
| `MemoryManager.load_state(data: Dict[str, Any])` | Method | Restores the manager's state from a provided dictionary, performing safe key mapping. |
| `MemoryManager.get_agent_memory(agent_name: str)` | Method | Retrieves the `AgentMemory` object for a specific agent or `None` if not found. |
| `MemoryManager.add_message_to_agent(target_agent: str, message_payload: Dict[str, Any])` | Method | Appends a message to an agent's incoming queue, creating the agent if necessary. |
| `MemoryManager.record_tool_result(agent_name: str, tool_name: str, params: Dict[str, Any], result: Dict[str, Any])` | Method | Logs tool outcomes to the global context and notifies the executing agent. |
| `MemoryManager.update_agent_history_and_notes(agent_name: str, response: Dict[str, Any])` | Method | Transitions messages from "received" to "history" and updates the agent's internal notes and manifest. |
| `MemoryManager.check_stagnation(tool_name: Optional[str], params: Dict[str, Any])` | Method | Analyzes recent tool calls to detect if the system is stuck in a repetitive loop. |
| `MemoryManager.clear(agent: str)` | Method | Resets the state of a specific agent and wipes the global tool result history. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **State Transition:** The `update_agent_history_and_notes` method implements a lifecycle for messages, moving them from a temporary `messages_received` buffer into a permanent `history` log to maintain chronological context.
    - **Loop Detection:** The `check_stagnation` method uses a fingerprinting mechanism (`tool_name` + sorted `params` JSON) and a sliding window of the last 5 actions to detect if a specific tool call has been repeated 3 or more times.
    - **Serialization:** Uses Python's `asdict` for deep conversion of dataclasses into standard dictionaries for easy JSON compatibility.
- **Side Effects:** 
    - **State Mutation:** Heavily mutates the internal `self.context` and `self.agents` dictionaries.
    - **Context Progression:** Calling `record_tool_result` with a `"SUCCESS"` status automatically increments the `current_step_index` in the global orchestrator context.
- **Error Handling:** 
    - The `load_state` method implements "safe mapping," meaning it only updates attributes that already exist on the dataclasses, preventing crashes if a serialized state contains deprecated or foreign keys.
    - `get_agent_memory` and `update_agent_history_and_notes` perform null checks on agent existence to prevent `KeyError`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `json`, `dataclasses`, `typing`.
- **Internal:** None.