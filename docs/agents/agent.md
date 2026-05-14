## 1. Architectural Role
Acts as a high-level facade and event-driven entry point that orchestrates the agentic lifecycle by integrating LLM connectivity, tool registries, and message orchestration via a configurable pipeline.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_pipeline_config` | Func | Parses JSON pipeline configurations and validates the existence of associated prompt files relative to the root directory. |
| `Agent` | Class | Encapsulates the agentic loop, managing the lifecycle of the orchestrator and propagating system events. |
| `Agent.__init__` | Method | Initializes core components: `ToolRegistry`, `LLMConnector`, and `MessageOrchestrator`, while binding event listeners. |
| `Agent.run` | Method | Executes the agentic turn by triggering lifecycle events and delegating the execution loop to the orchestrator. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `Agent` instance is created with a `prog` object and a `pipeline_file` path.
    2. `load_pipeline_config` is invoked to resolve absolute paths for the pipeline and all referenced `prompt_file` entries.
    3. `ToolRegistry` is instantiated as a singleton.
    4. `LLMConnector` is initialized using `prog.llm`.
    5. `MessageOrchestrator` is instantiated with the connector, registry, pipeline config, and `prog.modules`.
    6. Event listeners are bound to bridge `EVENT_BEFORE_LLM_REQUEST` and `EVENT_AFTER_LLM_REQUEST` from the orchestrator to the `Agent` instance.
- **Data Path**: 
    `user_prompt` (str) $\rightarrow$ `Agent.run()` $\rightarrow$ `self.trigger("before_agent_turn")` $\rightarrow$ `self.orchestrator.run_loop(user_prompt, session_id)` $\rightarrow$ `self.trigger("after_agent_turn")`.
- **Conditional Branching**:
    - **Pipeline Loading**: If `pipeline_file` does not exist or JSON parsing fails, returns an empty dict and raises `ValueError` in `Agent.__init__`.
    - **Prompt Validation**: If an agent's `prompt_file` is missing from the filesystem, the loading process aborts and returns an empty dict.
    - **Session Management**: If `session_id` is `None` during `run()`, a new `uuid4` string is generated; otherwise, the provided ID is used.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `json`, `uuid`
- **Internal Modules**: `functions` (as `func`), `config.ProgramSetting`, `tools.tool_registry.ToolRegistry`, `.llm_connector.LLMConnector`, `.message_orchestrator.MessageOrchestrator`, `core.events.Events`
- **External Packages**: None explicitly imported (relies on internal `prog` object for LLM/Module access)

## 5. Configuration & Environment
- **Hardcoded Constants**: `pipelines/default.json` (default `pipeline_file` argument).
- **Environment Lookups**: 
    - `prog.config.get(ProgramSetting.ROOT_DIRECTORY)` (used for path resolution).
    - `agent_data.get("prompt_file")` (retrieved from pipeline JSON).