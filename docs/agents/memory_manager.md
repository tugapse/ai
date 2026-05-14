## 1. Architectural Role

**Functional Mission**
The **MemoryManager** serves as the centralized state persistence and synchronization engine for the orchestration pipeline. Its primary mission is to maintain the integrity of both global orchestration context and individual agent-specific cognitive states, providing mechanisms to serialize, hydrate, and manipulate memory to ensure continuity across execution cycles.

**System Context & Integration**
This component acts as the authoritative source of truth for the state of all active agents and the global orchestrator. It integrates deeply with the agentic workflow by capturing tool execution results, managing message queues, and tracking historical interactions to prevent infinite loops. It provides the necessary state-management primitives that allow the system to recover from interruptions and maintain a coherent "thought process" as data flows between agents and the orchestration layer.

## 2. Environment & Configuration

**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `notes` (Default: `"System initialized."`)  Initial state for a new agent's internal notes.
- `current_task` (Default: `"Waiting for tasks..."`)  Initial state for an agent's task assignment.
- `occurrences` (Threshold: `3`)  The number of identical tool calls required to trigger stagnation detection.
- `action_history_fp` (Limit: `5`)  The sliding window size for tracking tool execution fingerprints.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentMemory` | Class | Data structure holding an agent's notes, message queues, history, current task, and manifest. |
| `OrchestratorContext` | Class | Data structure holding global tool results, current task, execution plan, step index, and action history. |
| `MemoryManager` | Class | The primary controller for managing, serializing, and hydrating agent and orchestrator states. |
| `serialize` | Method | Converts the live `MemoryManager` state into a dictionary for persistence. |
| `hydrate` | Method | Restores the `MemoryManager` state from a dictionary, mapping keys to existing attributes. |
| `get_agent_memory` | Method | Retrieves the `AgentMemory` instance for a specific agent name. |
| `add_message_to_agent` | Method | Appends a payload to an agent's `messages_received` queue, creating the agent if necessary. |
| `record_tool_result` | Method | Logs tool outputs to the global context and updates the agent's message queue. |
| `update_agent_history_and_notes` | Method | Transitions received messages into permanent history and updates agent notes/manifests. |
| `check_stagnation` | Method | Detects architectural loops by comparing current tool calls against a recent history of fingerprints. |
| `clear` | Method | Resets the state of a specific agent and wipes the global tool results. |

## 4. Execution Logic & Flow

- **Initialization**: The `MemoryManager` instantiates an empty `OrchestratorContext` and populates a dictionary of `AgentMemory` objects based on a provided list of agent names.
- **Data Path**:
    - **Input**: Tool results, agent responses, or external state dictionaries.
    - **Processing**: 
        - Tool results are appended to `context.tool_results` and used to increment `current_step_index`.
        - Agent responses trigger a migration where `messages_received` are moved to `history`, and new `thought`/`response` pairs are appended.
        - Stagnation check generates a JSON-sorted fingerprint of `tool_name` and `params` to track repetition.
    - **Output**: Serialized dictionaries for storage or hydrated objects for state recovery.
- **Conditional Branching**:
    - **Hydration Logic**: During `hydrate`, the system checks `hasattr` before setting values to ensure compatibility with evolving schemas.
    - **Stagnation Logic**: If the count of a specific tool fingerprint in the last 5 actions reaches $\ge 3$, `check_stagnation` returns `True` and sets `repeat_count`.
    - **Tool Success**: If a tool result contains `"status": "SUCCESS"`, the `current_step_index` is automatically incremented.

## 5. Resource Dependencies

- **Standard Libraries**: `json`, `dataclasses`, `typing`
- **Internal Modules**: 
    - No internal modules imported; logic is self-contained within the file.
- **External Packages**: None identified.