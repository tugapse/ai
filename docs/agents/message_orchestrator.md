## 1. Architectural Role
The `MessageOrchestrator` acts as the central nervous system for multi-agent workflows, managing the lifecycle of agentic execution, routing, and state persistence. It coordinates between the [llm_connector](agents/llm_connector.md) for LLM interaction, the [memory_manager](agents/memory_manager.md) for agent-specific context, and the [context_sentinel](agents/context_sentinel.md) for token limit enforcement. By integrating the [session_vault](agents/session_vault.md), it enables seamless session hydration and state re-inflation, allowing complex, multi-step tasks to persist across execution boundaries while managing tool authorization via a gatekeeper mechanism.

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramConfig.current` (via `ProgramConfig`)  Retrieves global runtime settings including agent thought visibility.
- `ProgramSetting.AGENT_THOUGHT` (via `ProgramConfig`)  Boolean flag to enable/disable thought process logging.

**Hardcoded Constants:**
- `MAX_ITERATIONS` (Default: `100`)  Maximum loop cycles allowed per execution.
- `MANAGER_AGENT_ROLE` (Default: `"management"`)  Identifier for agents acting as high-level orchestrators.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MessageOrchestrator` | Class | Main controller for multi-agent routing, state hydration, and loop execution. |
| `run_loop` | Method | The primary entry point that manages the iterative execution cycle and session recovery. |
| `_capture_state` | Method | Serializes current agent, iteration, and memory states for persistence. |
| `_apply_state` | Method | Re-injects serialized data from the `SessionVault` into active managers. |
| `_assemble_agent_tools` | Method | Filters the `ToolRegistry` to provide an agent with only its permitted toolset. |
| `_prepare_payload` | Method | Constructs the structured dictionary sent to the LLM, including history and context. |
| `_process_agent_response` | Method | Parses LLM output to handle tool calls, user clarifications, or agent transitions. |
| `_handle_tool_execution` | Method | Executes authorized tools via the registry and manages specialist overrides. |
| `_initialize_session_modules`| Method | Dynamically registers tools from external modules into the central `ToolRegistry`. |
| `_handle_format_error` | Method | Manages retry logic and error signaling when the LLM produces malformed output. |
| `_gatekeeper` | Method | Provides a human-in-the-loop authorization prompt for sensitive tool usage. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Instantiates managers: `SpecialistManager`, `ContextSentinel`, and `MemoryManager`.
    2. Sets up empty state for `SessionVault` and `vector_memory`.
- **Data Path**:
    1. **Input**: `user_prompt` + `session_id`.
    2. **Hydration**: `SessionVault` loads previous state $\rightarrow$ `_apply_state` updates managers.
    3. **Loop Start**: Identify `current_agent` $\rightarrow$ `_assemble_agent_tools` $\rightarrow$ `_prepare_payload`.
    4. **Refinement**: `ContextSentinel` distills payload if token limits are near.
    5. **LLM Request**: `connector.send_request` $\rightarrow$ LLM Response.
    6. **Parsing**: `_process_agent_response` extracts `action` (tool/target/message).
    7. **Execution**: `_handle_tool_execution` $\rightarrow$ `ToolRegistry` $\rightarrow$ Memory Update.
    8. **Output**: Transition to `next_agent` or `DONE`/`STOP`.
- **Conditional Branching**:
    - **Session Status**: If `vault.hydrate()` returns data, resume; else, start fresh with `entry_point`.
    - **Format Integrity**: If LLM output is invalid, `_handle_format_error` triggers a system-level correction message to the agent.
    - **Target Validation**: If `agent_target` is `USER`, pause for terminal input; if `STOP`, terminate loop.
    - **Tool Authorization**: If tool is not in `auto_authorized_tools`, trigger `_gatekeeper` manual prompt.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `json`, `typing`
- **Internal Modules**: 
    - `config.md`
    - `functions.md`
    - `color.md`
    - `terminal_ui.md` (via `agents/terminal_ui.md`)
    - `specialist_manager.md` (via `agents/specialist_manager.md`)
    - `memory_manager.md` (via `agents/memory_manager.md`)
    - `context_sentinel.md` (via `agents/context_sentinel.md`)
    - `session_vault.md` (via `agents/session_vault.md`)
    - `events.md` (via `core/events.md`)
    - `vector_memory.md` (via `modules/memory/vector_memory.md`)
- **External Packages**: None identified.