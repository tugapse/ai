## 1. Architectural Role
This file serves as the high-level Facade for the agentic system, implementing the [agent.py](src/ai/agents/agent.py) class. It encapsulates the complexity of the agentic loop by orchestrating the interaction between the [message_orchestrator.md](src/ai/agents/message_orchestrator.md), the [llm_connector.md](src/ai/agents/llm_connector.md), and the [tool_registry.md](tools/tool_registry.md). Its primary responsibility is to manage the lifecycle of an agent session, load pipeline configurations, and propagate system-wide events via the [events.md](core/events.md) mechanism.

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramSetting.ROOT_DIRECTORY` (via `prog.config.get`)  Locates the base directory for resolving relative file paths.

**Hardcoded Constants:**
- `pipelines/default.json` (Default: `"pipelines/default.json"`)  The fallback path for the agent pipeline configuration.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_pipeline_config` | Func | Parses JSON pipeline configs and validates that associated prompt files exist on disk. |
| `Agent` | Class | The primary entry point for agent execution; inherits from [events.md](core/events.md). |
| `Agent.__init__` | Method | Bootstraps core components: `ToolRegistry`, `LLMConnector`, and `MessageOrchestrator`. |
| `Agent.run` | Method | Executes the agentic loop for a specific `user_prompt`, managing session ID generation and event triggering. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Inherits event-triggering capabilities from [events.md](core/events.md).
    2. Executes `load_pipeline_config` to resolve absolute paths for the pipeline and its required prompt files.
    3. Instantiates `ToolRegistry` (Singleton).
    4. Initializes `LLMConnector` using the provided `prog.llm`.
    5. Initializes `MessageOrchestrator` with the connector, registry, config, and `prog.modules`.
    6. Binds orchestration events (`EVENT_BEFORE_LLM_REQUEST`, `EVENT_AFTER_LLM_REQUEST`) to the Agent's local event trigger.
- **Data Path**: 
    - `user_prompt` (str) $\rightarrow$ `Agent.run()` $\rightarrow$ `orchestrator.run_loop()` $\rightarrow$ `LLM Request/Response Cycle`.
- **Conditional Branching**: 
    - If `session_id` is `None`, a new `uuid4` string is generated.
    - If `pipeline_file` path is not absolute, it is joined with `ROOT_DIRECTORY`.
    - If any prompt file specified in the config is missing, the configuration loading fails and returns an empty dict.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `json`, `uuid`
- **Internal Modules**: 
    - [functions.md](functions.md)
    - [config.md](config.md)
    - [tools/tool_registry.md](tools/tool_registry.md)
    - [agents/llm_connector.md](agents/llm_connector.md)
    - [agents/message_orchestrator.md](agents/message_orchestrator.md)
    - [core/events.md](core/events.md)
- **External Packages**: None identified.