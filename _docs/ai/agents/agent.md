## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Agent | /ai/agents/agent.md |

This component provides the high-level facade (`Agent` class) for managing and executing complex agentic workflows. Its primary responsibility is to encapsulate the entire lifecycle of an agent run, from initial configuration loading to the final execution loop, abstracting the underlying machinery of the LLM, tools, and orchestration.

It serves as the primary controller layer within the application architecture. It initializes and manages the core services—such as the [ToolRegistry](/ai/tools/tool_registry.md), [LLMConnector](/ai/agents/llm_connector.md), and [AgentOrchestrator](/ai/agents/agent_orchestrator.md)—based on a provided pipeline configuration, allowing the system to run defined, multi-step autonomous tasks.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `load_pipeline_config` | Function | Loads and validates the pipeline configuration from disk, searching multiple defined paths. Returns config dict or empty dict on failure. |
| `build_orchestrator` | Function | Constructs and returns a fully initialized [AgentOrchestrator](/ai/agents/agent_orchestrator.md) by loading the pipeline and wiring up all necessary components. |
| `Agent` | Class | The main agent facade responsible for initializing components and running the agent loop. |
| `Agent.__init__` | Method | Initializes the agent by loading the pipeline and setting up the orchestrator and registry. |
| `Agent.run` | Method | Executes the agent's operational loop using a user prompt, managing session IDs. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `Agent` class orchestrates initialization by first calling `load_pipeline_config` to validate the execution plan. It then instantiates the `LLMConnector`, `ToolRegistry`, and `AgentOrchestrator`. The `run` method manages the session state and delegates the main execution flow to the orchestrator's `run_loop`. `build_orchestrator` similarly chains these dependencies together.
- **Side Effects:** Reads/writes to the filesystem (via `load_pipeline_config` for configuration and prompt templates). Interacts with external services via the `LLMConnector` when the orchestrator runs.
- **Error Handling:** `load_pipeline_config` handles file-not-found and JSON parsing errors, returning `{}` or logging an error via `func.error`. `build_orchestrator` explicitly raises a `ValueError` if the pipeline cannot be loaded or if the LLM is not initialized.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `json`, `uuid`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.config](/ai/config.md), [ai.services.directory_manager](/ai/services/directory_manager.md), [ai.tools.tool_registry](/ai/tools/tool_registry.md), [ai.agents.llm_connector](/ai/agents/llm_connector.md), [ai.agents.agent_orchestrator](/ai/agents/agent_orchestrator.md), [ai.core.events](/ai/core/events.md).