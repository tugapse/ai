## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | AgentOrchestrator |
| Source file | agent_orchestrator.py |

The **AgentOrchestrator** serves as the central nervous system of the multi-agent execution framework. It is responsible for managing the lifecycle of an agentic workflow, handling the routing of tasks between specialized agents, and maintaining the continuity of state through complex, multi-step reasoning loops.

**Functional Mission**
The primary mission of the **AgentOrchestrator** is to manage the execution loop of a multi-agent pipeline. It solves the problem of agent coordination by acting as a stateful controller that handles context distillation, tool authorization, agent-to-agent transitions, and session persistence. It ensures that the LLM receives a coherent, optimized payload while preventing infinite loops caused by parsing errors or stagnation.

**System Context & Integration**
The orchestrator sits at the highest level of the agentic execution layer. It integrates [LLMConnector](/docs/ai/agents/llm_connector.md) for model communication, [ToolRegistry](/docs/ai/tools/tool_registry.md) for capability management, and [MemoryManager](/docs/ai/agents/memory_manager.md) for agent-specific state. It utilizes [ContextSentinel](/docs/ai/agents/context_sentinel.md) to prevent context window overflow and [AgentSessionManager](/docs/ai/agents/session_manager.md) to ensure that long-running tasks can be resumed across different execution instances. When an agent requires specialized deep-dive capabilities, it delegates to the [SpecialistManager](/docs/ai/agents/specialist_manager.md).

- **INTERNAL REFERENCES**: 
    - [LLMConnector](/docs/ai/agents/llm_connector.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
    - [MemoryManager](/docs/ai/agents/memory_manager.md)
    - [ContextSentinel](/docs/ai/agents/context_sentinel.md)
    - [AgentSessionManager](/docs/ai/agents/session_manager.md)
    - [SpecialistManager](/docs/ai/agents/specialist_manager.md)
    - [MCPBridge](/docs/ai/tools/mcp_bridge.md)
    - [TerminalUI](/docs/ai/agents/terminal_ui.md)
    - [ModuleRegistry](/docs/ai/services/module_registry.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `mcp_config` (via `__init__`)  Locates the MCP server configuration file using `func.get_root_directory()`.

**Hardcoded Constants:**
- `MAX_ITERATIONS` (Default: `100`)  The maximum number of steps allowed in a single execution loop.
- `MANAGER_AGENT_ROLE` (Default: `"management"`)  Identifier for agents acting in a management capacity.
- `STOP_SIGNAL` (Default: `"STOP"`)  Signal used to terminate agent transitions.
- `MASTER_AGENT` (Default: `"MASTER"`)  The default fallback agent for routing.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentOrchestrator` | Class | The main controller for multi-agent orchestration and state management. |
| `run_loop` | Method | The primary entry point that executes the iterative agent reasoning cycle. |
| `_get_saved_session` | Method | Hydrates the orchestrator state from a persistent session. |
| `_capture_state` | Method | Serializes the current memory and orchestration metadata for persistence. |
| `_apply_state` | Method | Injects serialized state back into the active managers. |
| `_assemble_agent_tools` | Method | Filters and aggregates tools available to a specific agent. |
| `_prepare_payload` | Method | Constructs the structured dictionary sent to the LLM. |
| `_process_agent_response` | Method | Parses LLM output to determine the next action, tool call, or agent transition. |
| `_handle_tool_execution` | Method | Manages the lifecycle of a tool call, including specialist invocation and gatekeeping. |
| `_handle_format_error` | Method | Implements retry logic and error messaging when LLM output fails parsing. |
| `_gatekeeper` | Method | Provides a human-in-the-loop authorization interface for sensitive tools. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Initializes core connectors ([LLMConnector], [ToolRegistry], [ModuleRegistry]).
    2. Sets up specialized managers ([SpecialistManager], [ContextSentinel], [MCPBridge]).
    3. Loads MCP server configurations from the filesystem.
    4. Initializes [MemoryManager] for all defined agents.
- **Data Path**: 
    1. **Input**: `user_prompt` and `session_id` are passed to `run_loop`.
    2. **Hydration**: `_get_saved_session` checks for existing state; if found, `_apply_state` restores memory and context.
    3. **Iteration Loop**:
        - **Context Assembly**: `_prepare_payload` gathers history, plans, and recent tool outcomes.
        - **Optimization**: `context_sentinel.enforce_limits` compresses the payload if necessary.
        - **LLM Request**: `llm_connector.send_request` generates a response.
        - **Response Processing**: `_process_agent_response` extracts `thought`, `response_to_user`, and `action`.
        - **Tool Execution**: If an action is a tool call, `_handle_tool_execution` runs it via `tool_registry`.
        - **Routing**: The `next_agent` is determined based on the action's `agent_target`.
    4. **Persistence**: `session_manager.commit` saves the state after every successful iteration.
    5. **Output**: The loop terminates when `STOP_SIGNAL` is reached, `DONE` is returned, or `MAX_ITERATIONS` is exceeded.
- **Conditional Branching**:
    - **Parsing Failure**: If the LLM returns an invalid format, `_handle_format_error` increments a counter; if it hits 3, the loop breaks.
    - **Authorization**: `_gatekeeper` intercepts `execute_command` calls, prompting the user for `y/n/all` permission.
    - **Target Validation**: `_validate_target` ensures transitions only occur between allowed agents or the `USER`.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `json`, `typing`
- **Internal Modules**: 
    - [LLMConnector](/docs/ai/agents/llm_connector.md)
    - [Functions](/docs/ai/functions.md)
    - [ProgramConfig](/docs/ai/config.md)
    - [TerminalUI](/docs/ai/agents/terminal_ui.md)
    - [SpecialistManager](/docs/ai/agents/specialist_manager.md)
    - [ContextSentinel](/docs/ai/agents/context_sentinel.md)
    - [MCPBridge](/docs/ai/tools/mcp_bridge.md)
    - [MemoryManager](/docs/ai/agents/memory_manager.md)
    - [AgentSessionManager](/docs/ai/agents/session_manager.md)
    - [Events](/docs/ai/core/events.md)
    - [ModuleRegistry](/docs/ai/services/module_registry.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
- **External Packages**: None identified.