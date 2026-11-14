## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| AgentRunsService | /ai/modules/server/services/agent_runs.md |

This component is responsible for managing the lifecycle of agent execution instances running over HTTP. It provides the core service layer for starting, tracking, and controlling individual agent runs, ensuring that the server's shared model is used correctly across concurrent requests. It handles the entire workflow, from receiving a user prompt to logging the final outcome.

This service acts as the primary controller for agent execution within the server architecture. It integrates with the [BrainHub](/ai/modules/server/brain_hub.md) to manage model loading, uses [AgentRun](/ai/modules/server/services/agent_runs.md#agentrun) to maintain the state of a single execution, and relies on [WebAgentIO](/ai/modules/server/services/agent_runs.md#webagentio) to communicate events and request user permissions via the web client.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| AgentApiError | Class | Custom exception raised when the agent server refuses a request, carrying an HTTP status code. |
| WebAgentIO | Class | Handles communication between the agent orchestrator and the HTTP client, emitting events and blocking for permission answers. |
| AgentRun | Class | Encapsulates the complete state of a single agent run, including its event log, pending decisions, and orchestrator. |
| AgentRunService | Class | The main service managing the initiation, tracking, and lifecycle control of all agent runs. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `AgentRunService` manages a single active run via a thread-safe lock. When `start` is called, it validates inputs, loads the required model via the [BrainHub](/ai/modules/server/brain_hub.md), and spawns a background thread (`_run`) to execute the `AgentOrchestrator.run_loop`. This loop processes events and interacts with the underlying tools, pausing execution when waiting for permissions managed by `WebAgentIO`.
- **Side Effects:** The code heavily interacts with the filesystem (creating/reading/writing workspaces and sessions via [DirectoryManager](/ai/modules/server/services/directory_manager.md) and [AgentSessionManager](/ai/agents/session_manager.md)). It also spawns background threads for running agent loops and interacts with the shared model state in the [BrainHub](/ai/modules/server/brain_hub.md).
- **Error Handling:** It raises `AgentApiError` for input validation issues (400/404), concurrency issues (409), and permission denials (401/403). The run loop catches generic exceptions and logs them as an "error" event before finalizing the run.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are directly used by the service logic itself, relying instead on configuration passed via `ProgramSetting` or derived from the filesystem.

**Module Dependencies:**
- **Standard/External:** `os`, `re`, `threading`, `time`, `uuid`, `typing`, `json`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.agents.agent_io](/ai/agents/agent_io.md), [ai.config](/ai/config.md), [ai.services.directory_manager](/ai/modules/server/services/directory_manager.md), [ai.agents.tool_preview](/ai/agents/tool_preview.md).