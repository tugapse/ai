## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **MemoryManager** | [src/ai/agents/memory_manager.py](/AgentDocs/ai/agents/memory_manager.md) |

The `MemoryManager` is a centralized state management system designed to handle the persistence and lifecycle of agent-specific data and global orchestration context. It solves the problem of state fragmentation in multi-agent systems by providing a single source of truth for agent histories, current tasks, and tool execution results.

Within the broader application architecture, this component acts as a data controller for the agentic workflow. It facilitates the serialization of the entire system state, allowing for session persistence, and provides mechanisms to detect architectural loops (stagnation) through tool call fingerprinting. It serves as the connective tissue between individual agent reasoning and the global orchestration plan.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentMemory` | Class | A dataclass representing the internal state of a single agent, including notes, messages, history, and manifest metadata. |
| `OrchestratorContext` | Class | A dataclass representing the global state of the orchestration pipeline, including tool results, the active plan, and loop detection counters. |
| `MemoryManager` | Class | The primary controller for managing `AgentMemory` and `OrchestratorContext` instances. |
| `MemoryManager.__init__(agent_names: List[str])` | Constructor | Initializes the manager with a global context and a dictionary of `AgentMemory` objects for the specified agent names. |
| `MemoryManager.serialize()` | Method | Collapses the current live state of the context and all agents into a serializable `Dict[str, Any]`. |
| `MemoryManager.load_state(data: Dict[str, Any])` | Method | Restores the manager's state from a dictionary, performing safe key mapping to handle changes in the agent pool. |
| `MemoryManager.get_agent_memory(agent_name: str)` | Method | Retrieves the `AgentMemory` object associated with the provided name, or `None` if not found. |
| `MemoryManager.add_message_to_agent(target_agent: str, message_payload: Dict[str, Any])` | Method | Appends a message to an agent's received queue, creating the agent's memory on-demand if necessary. |
| `MemoryManager.record_tool_result(agent_name: str, tool_name: str, params: Dict[str, Any], result: Dict[str, Any])` | Method | Logs tool execution results to the global context, increments the orchestration step on success, and notifies the executing agent. |
| `MemoryManager.update_agent_history_and_notes(agent_name: str, response: Dict[str, Any])` | Method | Transitions messages from "received" to "history" and updates the agent's internal notes and manifest based on a response payload. |
| `MemoryManager.check_stagnation(tool_name: Optional[str], params: Dict[str, Any])` | Method | Detects potential infinite loops by tracking the frequency of identical tool call fingerprints in recent history. |
| `MemoryManager.clear(agent: str)` | Method | Resets the state of a specific agent and clears the global tool result history. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **State Management:** Uses Python `dataclasses` and `asdict` for efficient serialization and state mapping.
    - **Loop Detection:** Implements a sliding window of the last 5 tool call fingerprints (`tool_name` + sorted JSON `params`). If a single fingerprint appears 3 or more times within this window, `check_stagnation` returns `True`.
    - **Memory Transition:** The `update_agent_history_and_notes` method implements a "flush" mechanism where `messages_received` are moved into the permanent `history` log to clear the immediate input buffer.
- **Side Effects:** 
    - Mutates the internal `OrchestratorContext` and `AgentMemory` objects in-place.
    - Does not perform direct I/O; serialization/deserialization is handled via dictionary passing, leaving filesystem or network persistence to the caller.
- **Error Handling:** 
    - Uses safe dictionary access (`.get()`) and `hasattr` checks during `load_state` to prevent crashes when loading stale or incompatible state data.
    - Returns `None` gracefully when attempting to retrieve non-existent agent memories.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `json`: For fingerprint generation and parameter serialization.
    - `dataclasses`: For structured state definitions.
    - `typing`: For type hinting.
- **Internal:** 
    - No internal module imports present in this file.