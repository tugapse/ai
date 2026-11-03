## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **AgentOrchestrator** | [src/ai/agents/agent_orchestrator.py](/AgentDocs/ai/agents/agent_orchestrator.md) |

The `AgentOrchestrator` is the central engine responsible for managing multi-agent execution, routing, and state persistence. It coordinates the lifecycle of an agentic workflow, ensuring that tasks are passed between specialized agents, tools are correctly assigned, and the conversation context remains within LLM limits.

As a high-level controller within the agentic architecture, it integrates several critical subsystems: it uses [SpecialistManager](/AgentDocs/ai/agents/specialist_manager.md) for specialized tasks, [ContextSentinel](/AgentDocs/ai/agents/context_sentinel.md) for context window management, and [AgentSessionManager](/AgentDocs/ai/agents/session_manager.md) for long-term session persistence. It serves as the primary loop that drives the transition from user input to multi-step autonomous reasoning and tool execution.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentOrchestrator(llm_connector, tool_registry, pipeline_config, module_registry)` | Class | The main orchestrator class. Requires an [LLMConnector](/AgentDocs/ai/agents/llm_connector.md), [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md), a pipeline configuration dictionary, and a [ModuleRegistry](/AgentDocs/ai/services/module_registry.md). |
| `run_loop(user_prompt: str, session_id: str)` | Method | The primary execution loop. It hydraties existing sessions or starts a new one, iterating through agent turns until a `STOP` signal or completion is reached. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The orchestrator operates on a state-machine principle. In each iteration of `run_loop`, it:
    1. Identifies the `current_agent`.
    2. Assembles available tools via [MCPBridge](/AgentDocs/ai/tools/mcp_bridge.md).
    3. Prepares a payload including recent outcomes and memory.
    4. Enforces context limits via the `ContextSentinel`.
    5. Dispatches the request to the LLM.
    6. Processes the response to determine the next agent (`target`) or tool execution.
    7. Commits the new state to the `AgentSessionManager` for persistence.
- **Side Effects:** 
    - **Filesystem:** Loads MCP server configurations from `mcp/mcp_servers.json`.
    - **Network/LLM:** Makes external calls to LLM providers via [LLMConnector](/AgentDocs/ai/agents/llm_connector.md).
    - **Terminal/UI:** Outputs status updates, thoughts, and authorization prompts to the user via [TerminalUI](/AgentDocs/ai/agents/terminal_ui.md).
    - **User Interaction:** Blocks execution to wait for user input during `USER` target transitions or tool authorization requests (`_gatekeeper`).
- **Error Handling:** 
    - Implements a "format error" counter; if an agent fails to produce a validly structured response 3 consecutive times, the orchestrator halts the loop to prevent infinite parsing errors.
    - Validates agent targets against an `allowed_targets` list defined in the agent's configuration.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `pipeline_config`  A dictionary defining the agent hierarchy, tool access, and `max_iterations`.
- `mcp/mcp_servers.json`  Local file used to configure the `MCPBridge`.

**Module Dependencies:**
- **Standard/External:** `os`, `copy`, `json`, `typing`.
- **Internal:**
    - [LLMConnector](/AgentDocs/ai/agents/llm_connector.md)
    - [functions](/AgentDocs/ai/functions.md)
    - [ProgramConfig](/AgentDocs/ai/config.md)
    - [Color](/AgentDocs/ai/color.md)
    - [TerminalUI](/AgentDocs/ai/agents/terminal_ui.md)
    - [SpecialistManager](/AgentDocs/ai/agents/specialist_manager.md)
    - [MemoryManager](/AgentDocs/ai/agents/memory_manager.md)
    - [ContextSentinel](/AgentDocs/ai/agents/context_sentinel.md)
    - [AgentSessionManager](/AgentDocs/ai/agents/session_manager.md)
    - [Events](/AgentDocs/ai/core/events.md)
    - [ModuleRegistry](/AgentDocs/ai/services/module_registry.md)
    - [ProcessManager](/AgentDocs/ai/services/process_manager.md)
    - [MCPBridge](/AgentDocs/ai/tools/mcp_bridge.md)
    - [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md)