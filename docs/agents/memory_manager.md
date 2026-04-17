## 1. Architectural Role
The `MemoryManager` serves as the centralized state coordinator, managing isolated memory buffers for individual agents and a shared global context for the orchestration pipeline.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentMemory` | Dataclass | Schema for agent-specific state: `notes`, `messages_received`, `history`, `current_task`, and `manifest`. |
| `OrchestratorContext` | Dataclass | Schema for global pipeline state: `tool_results`, `task`, `plan`, `current_step_index`, `action_history_fp`, and `repeat_count`. |
| `MemoryManager` | Class | Orchestrates the lifecycle and access of `AgentMemory` and `OrchestratorContext`. |
| `get_agent_memory` | Method | Retrieves the `AgentMemory` instance for a specific agent name. |
| `add_message_to_agent` | Method | Appends a message payload to an agent's `messages_received` queue. |
| `record_tool_result` | Method | Logs tool execution to global context, increments `current_step_index` on success, and notifies the agent. |
| `update_agent_history_and_notes` | Method | Commits `messages_received` to `history`, updates `notes`/`manifest`, and logs the agent's own response. |
| `check_stagnation` | Method | Detects infinite loops by tracking a sliding window of tool call fingerprints. |
| `clear` | Method | Resets a specific agent's memory and clears global `tool_results`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Instantiates a single `OrchestratorContext`.
    2. Populates a `agents` dictionary by mapping provided `agent_names` to new `AgentMemory` instances.
- **Data Path**: 
    - **Input**: External tool results or agent responses $\rightarrow$ **Processing**: `MemoryManager` updates corresponding `AgentMemory` or `OrchestratorContext` fields $\rightarrow$ **Output**: Updated state available via `get_agent_memory` or `context` attribute.
- **Conditional Branching**:
    - **Tool Success**: In `record_tool_result`, if `result.get("status") == "SUCCESS"`, the `current_step_index` is incremented.
    - **Stagnation Detection**: In `check_stagnation`, if the count of the current tool fingerprint in the last 5 actions is $\ge 3$, it returns `True` and sets `repeat_count`; otherwise, it returns `False` and resets `repeat_count` to 0.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `dataclasses`, `typing`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `5`: Maximum size of the `action_history_fp` sliding window.
    - `3`: Threshold for stagnation detection (identical calls).
    - `"System initialized."`: Default value for `AgentMemory.notes`.
    - `"Waiting for tasks..."`: Default value for `AgentMemory.current_task`.