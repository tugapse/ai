## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| AgentOrchestrator | ai/agents/agent_orchestrator |

This component serves as the central control plane for the entire multi-agent system. Its primary responsibility is to manage the execution flow, state transitions, and communication between various specialized agents throughout a complex task. It dictates the order of operations, handles context management, and ensures that the entire pipeline progresses logically from initiation to completion or failure.

The `AgentOrchestrator` acts as the primary controller layer within the application architecture. It orchestrates interactions with core services like [LLMConnector](/ai/agents/llm_connector.md), manages session persistence via [AgentSessionManager](/ai/agents/session_manager.md), and leverages context safety provided by [ContextSentinel](/ai/agents/context_sentinel.md). It sits above the individual agent logic, acting as the conductor for the ensemble.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentOrchestrator` | Class | Orchestrates multi-agent execution, routing, and state management. |
| `TurnResult` | Class | Outcome of a single `run_loop` call, detailing the reason, agent, and final message. |
| `AgentOrchestrator.emit` | Method | Shortcut to send an event through the I/O channel for logging or signaling. |
| `AgentOrchestrator.cancel` | Method | Requests the running loop to stop gracefully at the next safe point. |
| `AgentOrchestrator.close` | Method | Shuts down external resources managed by the orchestrator, such as MCP server processes. |
| `AgentOrchestrator.reset_state` | Method | Clears all in-memory agent state, preparing for a fresh session. |
| `AgentOrchestrator.run_loop` | Method | The main execution loop; runs the pipeline based on a user prompt and session ID. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `run_loop` implements a finite state machine driven by LLM outputs. It initializes or loads a session state, iterates through execution steps, prepares the prompt payload (including context distillation via [ContextSentinel](/ai/agents/context_sentinel.md)), invokes the LLM, and processes the response to determine the `next_agent`. State is persisted before each turn using [AgentSessionManager](/ai/agents/session_manager.md). Tool execution is gated by the `_gatekeeper` method, which interfaces with [AgentIO](/ai/agents/agent_io.md) for human-in-the-loop (HIL) approvals.

- **Side Effects:** The code extensively interacts with external systems. It reads/writes configuration via [ProgramConfig](/ai/config.md), communicates with the LLM via [LLMConnector](/ai/agents/llm_connector.md), reads/writes files/state via [MemoryManager](/ai/agents/memory_manager.md), and manages processes via [ProcessManager](/ai/services/process_manager.md). It also interacts with the file system to load MCP configurations via [DirectoryManager](/ai/services/directory_manager.md).

- **Error Handling:** Robust error handling exists for pipeline failures, including catching API errors from the LLM connector, detecting malformed LLM responses via `_handle_format_error` (which limits retries to 3), and managing session integrity checks during state loading (`_get_saved_session`).

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig` — Used to retrieve global runtime settings, such as `HIL_TOOLS` (list of tools requiring human approval) and `AGENT_THOUGHT` (boolean flag to enable thought logging).

**Module Dependencies:**
- **Standard/External:** `os`, `copy`, `json`, `threading`, `dataclasses`, `typing`.
- **Internal:** [LLMConnector](/ai/agents/llm_connector.md), [ToolRegistry](/ai/tools/tool_registry.md), [SpecialistManager](/ai/agents/specialist_manager.md), [ContextSentinel](/ai/agents/context_sentinel.md), [AgentSessionManager](/ai/agents/session_manager.md), [MemoryManager](/ai/agents/memory_manager.md), [AgentIO](/ai/agents/agent_io.md), [ProcessManager](/ai/services/process_manager.md), [DirectoryManager](/ai/services/directory_manager.md), [ModuleRegistry](/ai/services/module_registry.md), [MCPBridge](/ai/tools/mcp_bridge.md).