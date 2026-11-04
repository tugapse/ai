## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **AgentOrchestrator** | [src/ai/agents/agent_orchestrator.py](/src/ai/agents/agent_orchestrator.py) |

The `AgentOrchestrator` is the central engine responsible for managing multi-agent execution, routing, and state persistence. It coordinates the lifecycle of various specialized agents, ensuring that tasks are passed correctly between them, tool calls are authorized and executed, and the conversation context remains within LLM limits.

As a core controller within the agentic architecture, it integrates several critical subsystems: it uses [ContextSentinel](/AgentDocs/ai/agents/context_sentinel.md) for context distillation, [MemoryManager](/AgentDocs/ai/agents/memory_manager.md) for stateful intelligence, and [MCPBridge](/AgentDocs/ai/tools/mcp_bridge.md) for external tool integration. It acts as the bridge between high-level user intent and the low-level execution of individual agent turns.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentOrchestrator(llm_connector, tool_registry, pipeline_config, module_registry)` | Class | The main orchestrator class. Initializes specialized managers (Specialist, Context, MCP) and memory systems. |
| `run_loop(user_prompt, session_id)` | Method | The primary execution loop. It hydrates sessions, iterates through agent turns, handles tool execution, and manages transitions until a `STOP` signal or `DONE` state is reached. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The orchestrator operates on a state-machine principle. In each iteration of `run_loop`, it:
    1. Identifies the `current_agent`.
    2. Assembles available tools via [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md).
    3. Prepares an LLM payload, applying context compression via the `ContextSentinel`.
    4. Triggers events (`before_llm_request`, `after_llm_request`) via [Events](/AgentDocs/ai/core/events.md).
    5. Processes the LLM response to determine if a tool should be called, a message sent to a target agent, or a transition to a new agent should occur.
    6. Commits the resulting state to the [AgentSessionManager](/AgentDocs/ai/agents/session_manager.md) for persistence.
- **Side Effects:** 
    - **Filesystem:** Reads MCP configurations from `mcp/mcp_servers.json` and interacts with files via tool execution.
    - **Network:** Communicates with LLM providers through [LLMConnector](/AgentDocs/ai/agents/llm_connector.md).
    - **I/O:** Performs blocking `input()` calls for user authorization of sensitive tools (the "Gatekeeper" mechanism) and user clarifications.
    - **State Mutation:** Updates the global `ProcessManager` state to reflect current execution progress.
- **Error Handling:** 
    - Implements a `format_error_count` mechanism to detect and halt infinite loops caused by repeated LLM parsing failures (max 3 attempts).
    - Validates agent existence in memory and ensures target transitions are permitted by the agent's configuration.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `pipeline_config` (Dict)  Defines the agent graph, including `agents` definitions, `max_iterations`, and `entry_point`.
- `mcp_servers.json`  External configuration file used to load MCP server schemas.

**Module Dependencies:**
- **Standard/External:** `os`, `copy`, `json`, `typing`.
- **Internal:**
    - [LLMConnector](/AgentDocs/ai/agents/llm_connector.md)
    - [functions](/AgentDocs/ai/functions.md)
    - [ProgramConfig](/AgentDocs/ai/config.md)
    - [Color](/AgentDocs/ai/color.md)
    - [TerminalUI](/AgentDocs/ai/agents/terminal_ui.md)
    - [SpecialistManager](/AgentDocs/ai/agents/specialist_manager.md)
    - [ContextSentinel](/AgentDocs/ai/agents/context_sentinel.md)
    - [MCPBridge](/AgentDocs/ai/tools/mcp_bridge.md)
    - [MemoryManager](/AgentDocs/ai/agents/memory_manager.md)
    - [AgentSessionManager](/AgentDocs/ai/agents/session_manager.md)
    - [Events](/AgentDocs/ai/core/events.md)
    - [ModuleRegistry](/AgentDocs/ai/services/module_registry.md)
    - [ProcessManager](/AgentDocs/ai/services/process_manager.md)
    - [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md)