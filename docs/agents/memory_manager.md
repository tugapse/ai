## 1. Architectural Role
The `memory_manager.py` file serves as the centralized state synchronization engine for the orchestration pipeline. It provides a structured mechanism to maintain both global orchestration context via `OrchestratorContext` and individual agent-specific cognitive states via `AgentMemory`. Its primary responsibility is to facilitate state persistence (serialization/hydration), track tool execution histories to prevent infinite loops through stagnation detection, and manage the lifecycle of message queues and historical logs for all active agents within the system.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `notes` (Default: `"System initialized."`)  Initial state for a new agent's internal observations.
- `current_task` (Default: `"Waiting for tasks..."`)  Initial state for an agent's active objective.
- `occurrences_threshold` (Implicit: `3`)  Number of identical tool calls required to trigger stagnation detection.
- `history_window_size` (Implicit: `5`)  Maximum number of fingerprints kept in `action_history_fp` to detect loops.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentMemory` | Class | Dataclass representing the localized state, history, and manifest of a single agent. |
| `OrchestratorContext` | Class | Dataclass representing the global pipeline state, including tool results and task progress. |
| `MemoryManager` | Class | The primary controller for managing, persisting, and updating agent and orchestrator states. |
| `serialize` | Method | Transforms the live memory objects into a dictionary for JSON/persistence operations. |
| `hydrate` | Method | Restores state from a dictionary, safely mapping keys to existing attributes. |
| `get_agent_memory` | Method | Retrieves the `AgentMemory` object for a specific agent identifier. |
| `add_message_to_agent` | Method | Appends a payload to an agent's `messages_received` queue; initializes memory if missing. |
| `record_tool_result` | Method | Logs tool outputs to global context and agent messages; increments `current_step_index` on success. |
| `update_agent_history_and_notes` | Method | Transitions received messages to permanent history and updates agent thoughts/manifests. |
| `check_stagnation` | Method | Detects repetitive tool-parameter patterns to prevent architectural loops. |
| `clear` | Method | Resets an agent's memory and wipes the global tool result context. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Instantiates `OrchestratorContext`.
    - Maps `agent_names` to individual `AgentMemory` instances.
- **Data Path (Message Processing)**:
    - `add_message_to_agent` $\rightarrow$ `messages_received` queue.
    - `update_agent_history_and_notes` $\rightarrow$ moves `messages_received` to `history` $\rightarrow$ appends `SELF` thought/response $\rightarrow$ clears `messages_received`.
- **Data Path (Tool Execution)**:
    - `record_tool_result` $\rightarrow$ updates `context.tool_results` $\rightarrow$ checks `status == "SUCCESS"` $\rightarrow$ increments `current_step_index`.
- **Conditional Branching**:
    - `hydrate`: Checks `if not data` and `if hasattr` to ensure safe attribute assignment during state restoration.
    - `update_agent_history_and_notes`: Validates existence of memory via `if not memory`.
    - `check_stagnation`: Generates a fingerprint $\rightarrow$ checks if `occurrences >= 3` $\rightarrow$ returns `True` (loop detected) or `False`.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `dataclasses`, `typing`
- **Internal Modules**: 
    - [agents/memory_manager.md](agents/memory_manager.md)
- **External Packages**: None identified.