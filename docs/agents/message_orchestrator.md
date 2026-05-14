## 1. Architectural Role
Acts as the central execution engine that manages multi-agent lifecycles, routes LLM-generated actions, maintains state persistence via session hydration, and enforces context constraints.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MessageOrchestrator` | Class | Primary controller for agent orchestration, tool routing, and session state management. |
| `run_loop` | Method | Orchestrates the iterative execution cycle, handling session hydration and agent transitions. |
| `_capture_state` | Method | Serializes current memory, context plans, and tool authorization status for persistence. |
| `_apply_state` | Method | Re-injects serialized state into memory and context managers during session resumption. |
| `_assemble_agent_tools` | Method | Filters the global tool registry to provide a specific subset of tools to an agent. |
| `_prepare_payload` | Method | Constructs the structured dictionary (objective, history, plan, context) for LLM requests. |
| `_process_agent_response` | Method | Parses LLM output to execute tools, handle user interaction, or transition to new agents. |
| `_handle_tool_execution` | Method | Manages specialist tool invocation, security gatekeeping, and registry execution. |
| `_initialize_session_modules` | Method | Dynamically registers tools from all provided modules into the central registry. |
| `_handle_format_error` | Method | Manages error recovery and loop termination when an agent fails to produce valid output. |
| `_gatekeeper` | Method | Intercepts sensitive tool calls to request manual user authorization. |
| `_validate_target` | Method | Ensures agent-to-agent transitions adhere to defined pipeline constraints. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Instantiates specialized managers (`SpecialistManager`, `ContextSentinel`).
    2. Initializes `MemoryManager` with agent keys.
    3. Sets up `auto_authorized_tools` and error counters.
- **Data Path**: 
    1. **Input**: `user_prompt` and `session_id` enter `run_loop`.
    2. **Hydration**: `SessionVault` loads existing state; if empty, seeds initial memory with `user_prompt`.
    3. **Payload Construction**: `_prepare_payload` aggregates memory, plans, and recent outcomes $\rightarrow$ `ContextSentinel` applies compression/distillation.
    4. **LLM Request**: `connector.send_request` processes the payload $\rightarrow$ Returns `response`.
    5. **Action Processing**: `_process_agent_response` extracts `action` $\rightarrow$ `_handle_tool_execution` executes tools $\rightarrow$ Results are recorded in `MemoryManager`.
    6. **State Transition**: `_capture_state` serializes the new state $\rightarrow$ `SessionVault.commit` persists to disk.
    7. **Output**: The loop repeats with the `next_agent` or terminates on `STOP`/`DONE`.
- **Conditional Branching**:
    - **Session Check**: If `vault.hydrate()` succeeds, resume state; else, start fresh.
    - **Agent Validation**: If `current_agent` is not in `self.agents`, reset to `entry_point`.
    - **Response Status**: If `response["status"] == "FAILED"`, trigger `_handle_format_error` logic.
    - **Target Routing**: Branches based on `target` (e.g., `USER` triggers `input()`, `STOP` terminates, or valid agent transitions).
    - **Security**: `_gatekeeper` branches based on user `y/n/all` input for tool execution.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `json`, `typing`
- **Internal Modules**: `config`, `functions`, `color`, `terminal_ui`, `agents.specialist_manager`, `agents.memory_manager`, `agents.context_sentinel`, `agents.session_vault`, `core.events`
- **External Packages**: N/A (Relies on internal abstraction layers)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `MAX_ITERATIONS = 100`
    - `MANAGER_AGENT_ROLE = "management"`
- **Environment Lookups**: 
    - `ProgramConfig.current.get(ProgramSetting.AGENT_THOUGHT)` (Determines if agent reasoning is displayed).
    - `pipeline_config` (Dict containing `agents`, `entry_point`, `max_iterations`).