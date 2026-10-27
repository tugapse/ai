## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | MemoryManager |
| Source file | memory_manager.py |

The **MemoryManager** serves as the centralized state repository and persistence engine for the orchestration layer. It is responsible for maintaining the distinction between global orchestration context and individual agent-specific cognitive states, ensuring that as the system executes complex tasks, the history of actions, tool outputs, and internal agent reasoning remains coherent and recoverable.

**Functional Mission**
The primary responsibility of **MemoryManager** is to manage the lifecycle of stateful data within the agentic ecosystem. It solves the problem of state fragmentation by providing a unified interface to record tool executions, update agent histories, and detect execution loops (stagnation). Its core mission is to act as the "source of truth" for the current progress of a task and the accumulated knowledge of all participating agents.

**System Context & Integration**
This component acts as a critical data bridge between the execution engine and the agentic logic. It receives real-time updates from tool executions and agent responses, transforming them into structured history. It provides the necessary state data for [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md) to make informed decisions about the next step in a plan. Furthermore, its ability to serialize state allows for session persistence, which can be managed by higher-level services like [Session Manager](/docs/ai/services/session_manager.md).

- **INTERNAL REFERENCES**: [Agent Orchestrator](/docs/ai/agents/agent_orchestrator.md), [Session Manager](/docs/ai/services/session_manager.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `System initialized.` (Default: `AgentMemory.notes`)  Initial state for new agent notes.
- `Waiting for tasks...` (Default: `AgentMemory.current_task`)  Initial state for new agent tasks.
- `5` (Default: `check_stagnation` sliding window)  Maximum size of the action history fingerprint buffer.
- `3` (Default: `check_stagnation` threshold)  Number of identical tool calls required to trigger a stagnation flag.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentMemory` | Class | Data container for individual agent state (notes, messages, history, manifest). |
| `OrchestratorContext` | Class | Data container for global execution state (tool results, plan, step index, action history). |
| `MemoryManager` | Class | Primary controller for managing and persisting agent and orchestrator states. |
| `serialize` | Method | Converts the entire memory state into a dictionary for persistence. |
| `load_state` | Method | Reconstitutes the memory state from a dictionary with safety checks for agent pool changes. |
| `get_agent_memory` | Method | Retrieves the `AgentMemory` object for a specific agent name. |
| `add_message_to_agent` | Method | Appends a payload to an agent's `messages_received` queue. |
| `record_tool_result` | Method | Logs tool outcomes to global context and notifies the specific agent. |
| `update_agent_history_and_notes` | Method | Transitions messages from "received" to "history" and updates agent cognitive state. |
| `check_stagnation` | Method | Monitors tool call patterns to detect infinite loops or architectural stagnation. |
| `clear` | Method | Resets an agent's memory and clears the global tool results. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Instantiates an empty `OrchestratorContext`.
    2. Creates a dictionary of `AgentMemory` objects based on the provided `agent_names` list.
- **Data Path (Tool Execution)**: 
    1. `record_tool_result` receives `agent_name`, `tool_name`, `params`, and `result`.
    2. The result is appended to `context.tool_results`.
    3. If `result["status"] == "SUCCESS"`, `context.current_step_index` is incremented.
    4. The result is passed to `add_message_to_agent` to notify the agent via its `messages_received` queue.
- **Data Path (Agent Cognitive Update)**:
    1. `update_agent_history_and_notes` is called with an agent's response.
    2. `notes` and `manifest` are updated in the agent's memory.
    3. All items in `messages_received` are moved to the `history` list.
    4. A new "SELF" entry containing the agent's `thought` and `response_to_user` is appended to `history`.
    5. `messages_received` is cleared.
- **Conditional Branching (Stagnation Detection)**:
    1. `check_stagnation` generates a fingerprint string: `tool_name` + `json.dumps(params)`.
    2. The fingerprint is added to `action_history_fp`.
    3. If the buffer exceeds 5 entries, the oldest entry is popped.
    4. If the current fingerprint appears $\ge 3$ times in the buffer, `repeat_count` is set and `True` is returned.
    5. Otherwise, `repeat_count` is reset to 0 and `False` is returned.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `dataclasses`, `typing`
- **Internal Modules**: 
    - No direct internal module imports found in the provided source.
- **External Packages**: None identified.