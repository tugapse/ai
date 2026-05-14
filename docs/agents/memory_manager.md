## 1. Architectural Role
Centralizes and persists the stateful memory of individual agents and the global orchestration context to facilitate continuity and loop detection.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentMemory` | Class | Data structure for storing an agent's notes, message queues, history, current task, and manifest. |
| `OrchestratorContext` | Class | Data structure for storing global orchestration state including tool results, tasks, plans, and action history. |
| `MemoryManager` | Class | Primary controller for managing agent/context lifecycles, serialization, and state updates. |
| `__init__` | Method | Instantiates `OrchestratorContext` and a dictionary of `AgentMemory` objects based on provided names. |
| `serialize` | Method | Converts the entire live state into a dictionary format for persistence. |
| `hydrate` | Method | Restores state from a dictionary, mapping keys to existing attributes to ensure compatibility. |
| `get_agent_memory` | Method | Retrieves the `AgentMemory` instance associated with a specific agent name. |
| `add_message_to_agent` | Method | Appends a payload to an agent's `messages_received` list, creating the agent if missing. |
| `record_tool_result` | Method | Logs tool execution to global context, increments step index on success, and notifies the agent. |
| `update_agent_history_and_notes` | Method | Flushes `messages_received` into `history`, updates `notes` and `manifest`, and appends the agent's own thought/response. |
| `check_stagnation` | Method | Generates a fingerprint of tool calls to detect repeated patterns (>= 3 occurrences in last 5 calls). |
| `clear` | Method | Resets an agent's specific memory fields and clears the global `tool_results`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `MemoryManager` is instantiated with a list of `agent_names`.
    2. An `OrchestratorContext` is created with default empty lists/strings.
    3. A dictionary `self.agents` is populated with `AgentMemory` instances for every name in the input list.
- **Data Path**:
    - **Input (External/System)** $\rightarrow$ `record_tool_result` or `add_message_to_agent` $\rightarrow$ Updates `context.tool_results` or `agent.messages_received`.
    - **Input (Agent Response)** $\rightarrow$ `update_agent_history_and_notes` $\rightarrow$ `messages_received` is moved to `history` $\rightarrow$ `notes`/`manifest` are updated $\rightarrow$ `messages_received` is cleared.
    - **Input (State Dump)** $\rightarrow$ `serialize` $\rightarrow$ Dictionary output.
    - **Input (State Load)** $\rightarrow$ `hydrate` $\rightarrow$ Attribute-by-attribute update of existing objects.
- **Conditional Branching**:
    - `hydrate`: Checks if `data` exists; iterates through keys only if `hasattr` returns true to prevent injection of undefined attributes.
    - `record_tool_result`: Checks if `result.get("status") == "SUCCESS"` to decide whether to increment `context.current_step_index`.
    - `update_agent_history_and_notes`: Checks if `memory` exists for the requested `agent_name` before attempting updates.
    - `check_stagnation`: Compares `occurrences` of the current tool fingerprint against a threshold of 3; manages a sliding window of the last 5 actions.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `dataclasses` (`dataclass`, `field`, `asdict`), `typing` (`Dict`, `Any`, `Optional`, `List`).
- **Internal Modules**: None.
- **External Packages**: None.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `AgentMemory.notes` default: `"System initialized."`
    - `AgentMemory.current_task` default: `"Waiting for tasks..."`
    - `check_stagnation` window size: `5`
    - `check_stagnation` threshold: `3`
- **Environment Lookups**: None.