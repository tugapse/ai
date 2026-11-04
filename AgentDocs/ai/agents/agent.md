## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Agent** | [src/ai/agents/agent.py](/src/ai/agents/agent.py) |

The `Agent` component serves as a high-level facade that encapsulates the entire agentic execution loop. It is responsible for orchestrating the lifecycle of an agentic workflow, from loading pipeline configurations to managing the interaction between the Large Language Model (LLM) and available tools.

Within the broader system architecture, this component acts as the primary interface for running complex, multi-step agentic tasks. It integrates several core subsystems, including the [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md), [LLMConnector](/AgentDocs/ai/agents/llm_connector.md), and [AgentOrchestrator](/AgentDocs/ai/agents/agent_orchestrator.md), providing a unified entry point for user prompts and session management.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `load_pipeline_config(prog, pipeline_file: str) -> dict` | Function | Searches for and loads a JSON pipeline configuration. It validates that all referenced prompt files exist within the system prompts directory. |
| `Agent(prog, pipeline_file: str = "default.json")` | Class | The main agentic controller. Initializes the tool registry, LLM connector, and orchestrator. Inherits from [Events](/AgentDocs/ai/core/events.md). |
| `Agent.run(user_prompt: str, session_id: str = "")` | Method | Initiates the agent's execution loop. Handles session ID generation (via UUID) and delegates the loop to the orchestrator. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component follows a facade pattern. Upon initialization, it loads a JSON configuration that defines the agent's behavior and prompt templates. It then sets up an [AgentOrchestrator](/AgentDocs/ai/agents/agent_orchestrator.md) to handle the actual reasoning loop. The `Agent` class also acts as an event proxy, capturing events from the orchestrator (such as `EVENT_BEFORE_LLM_REQUEST`) and re-triggering them at the agent level.
- **Side Effects:** 
    - **Filesystem:** Reads pipeline configuration files and prompt templates from the disk via [DirectoryManager](/AgentDocs/ai/services/directory_manager.md).
    - **Logging:** Uses [func.log](/AgentDocs/ai/functions.md) to record session starts and errors.
    - **Network/LLM:** Triggers LLM requests through the [LLMConnector](/AgentDocs/ai/agents/llm_connector.md).
- **Error Handling:** 
    - Throws a `ValueError` if the pipeline configuration fails to load.
    - Uses `func.error` to report missing configuration files or missing prompt templates during the loading phase.
    - Returns an empty dictionary if JSON parsing fails.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are accessed within this file; it relies on the `prog` object to provide access to system configurations and directory paths.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `json`, `uuid`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.config](/AgentDocs/ai/config.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)
    - [ai.tools.tool_registry](/AgentDocs/ai/tools/tool_registry.md)
    - [ai.agents.llm_connector](/AgentDocs/ai/agents/llm_connector.md)
    - [ai.agents.agent_orchestrator](/AgentDocs/ai/agents/agent_orchestrator.md)
    - [ai.core.events](/AgentDocs/ai/core/events.md)