## 1. Architectural Role
The `MessageOrchestrator` manages the multi-agent execution lifecycle, routing tasks between agents, enforcing context window limits, and coordinating tool execution via a centralized memory and registry system.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MessageOrchestrator` | Class | Main controller for agent routing, state management, and LLM interaction loops. |
| `run_loop` | Method | Executes the primary iterative cycle of agent transitions until a termination state is reached. |
| `_assemble_agent_tools` | Method | Filters the global tool registry to provide an agent with only its authorized tools. |
| `_prepare_payload` | Method | Constructs the structured data object (objective, history, plan, memory) sent to the LLM. |
| `_process_agent_response` | Method | Parses LLM output to handle tool calls, user interactions, and agent-to-agent routing. |
| `_handle_tool_execution` | Method | Validates tool authorization and executes logic via `SpecialistManager` or `registry`. |
| `_initialize_session_modules` | Method | Connects the `vector_memory` instance from the `module_registry` to the orchestrator. |
| `_format_recent_outcomes` | Method | Truncates large tool results to prevent context window overflow. |
| `_handle_format_error` | Method | Manages retry logic and user abort prompts when LLM output fails parsing. |
| `_gatekeeper` | Method | Intercepts high-risk system tools to request manual user authorization. |
| `_validate_target` | Method | Ensures agent transitions adhere to the `allowed_targets` defined in the agent configuration. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Stores `connector`, `registry`, `pipeline_config`, and `module_registry`.
    2. Instantiates `SpecialistManager` with a predefined mapping of high-level roles.
    3. Instantiates `ContextSentinel` for token limit enforcement.
    4. Initializes `MemoryManager` using the list of agents from the config.
- **Data Path**: 
    `user_prompt` $\rightarrow$ `run_loop` $\rightarrow$ `_prepare_payload` (Context + Memory) $\rightarrow$ `ContextSentinel` (Compression) $\rightarrow$ `connector.send_request` $\rightarrow$ `_process_agent_response` $\rightarrow$ `_handle_tool_execution` $\rightarrow$ `MemoryManager` (Update) $\rightarrow$ `Next Agent`.
- **Conditional Branching**:
    - **Format Error**: If `response["status"] == "FAILED"`, increment `format_error_count`; if $\ge 3$, prompt user to quit.
    - **Target Routing**: If `target == "USER"`, pause for `input()`; if `target == "DONE"`, clear memory and return to `MASTER`; if `target == "STOP"`, terminate loop.
    - **Tool Authorization**: If tool is in `["execute_command", "patch_file", "write_file"]` and not in `auto_authorized_tools`, trigger `_gatekeeper` for manual approval.
    - **Specialist Routing**: If `specialist_manager.is_specialist_tool(tool_name)` is true, delegate content generation to the specialist before final tool execution.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `json`
- **Internal Modules**: `functions`, `color`, `terminal_ui`, `.specialist_manager`, `.memory_manager`, `.context_sentinel`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `MAX_ITERATIONS = 100`
    - `MANAGER_AGENT_ROLE = "management"`
    - `ContextSentinel` threshold: `0.6`, max_tokens: `600000`
    - `_format_recent_outcomes` length: `3000`
- **Environment Lookups**: None. (Relies on `pipeline_config` and `module_registry` passed during instantiation).