## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Agent |
| Source file | agent.py |

The **Agent** component serves as the high-level facade and primary entry point for the agentic execution loop. It abstracts the underlying complexity of orchestration, tool management, and LLM communication into a simplified interface, allowing users to trigger complex multi-step reasoning processes through a single `run` method.

**Functional Mission**
The primary responsibility of the **Agent** is to encapsulate the lifecycle of an agentic session. It manages the loading of pipeline configurations, initializes the necessary sub-systemsincluding the tool registry, LLM connector, and orchestratorand provides an event-driven interface to monitor the agent's internal state transitions.

**System Context & Integration**
The component acts as the bridge between the high-level user intent and the low-level execution logic managed by the [AgentOrchestrator](/docs/ai/agents/agent_orchestrator.md). It consumes configuration data to define the agent's behavior and propagates events from the orchestrator up to the caller via the [Events](/docs/ai/core/events.md) system. It relies on the [LLMConnector](/docs/ai/agents/llm_connector.md) for model communication and the [ToolRegistry](/docs/ai/tools/tool_registry.md) for capability discovery, effectively acting as the "brain's" external interface.

- **INTERNAL REFERENCES**: 
    - [AgentOrchestrator](/docs/ai/agents/agent_orchestrator.md)
    - [LLMConnector](/docs/ai/agents/llm_connector.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
    - [Events](/docs/ai/core/events.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [Functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `prog.config.get(ProgramSetting.ROOT_DIRECTORY)`  Retrieves the base directory of the project to resolve relative file paths for pipelines and prompts.

**Hardcoded Constants:**
- `default.json` (Default: `"default.json"`)  The fallback pipeline configuration filename if none is provided.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_pipeline_config` | Func | Resolves and parses the JSON pipeline configuration, validating the existence of associated prompt files. |
| `Agent` | Class | The main facade class that manages the agentic lifecycle and event propagation. |
| `Agent.__init__` | Method | Initializes core components: `ToolRegistry`, `LLMConnector`, and `AgentOrchestrator`. |
| `Agent.run` | Method | Executes the agentic loop for a specific user prompt, handling session creation or resumption. |

## 4. Execution Logic & Flow
- **Initialization**:
    1. Receives the `prog` object and a `pipeline_file` string.
    2. Calls `load_pipeline_config` to locate and validate the JSON configuration.
    3. Instantiates a `ToolRegistry`.
    4. Instantiates an `LLMConnector` using the program's LLM instance.
    5. Instantiates an `AgentOrchestrator` with the registry, connector, and loaded config.
    6. Binds orchestrator events (`EVENT_BEFORE_LLM_REQUEST`, `EVENT_AFTER_LLM_REQUEST`) to the Agent's own event trigger mechanism.
- **Data Path**:
    - **Input**: `user_prompt` (str) and optional `session_id` (str).
    - **Processing**: 
        - Triggers `before_agent_turn`.
        - Generates a new `uuid4` session ID if none is provided.
        - Passes control to `orchestrator.run_loop`.
    - **Output**: Execution results are handled internally by the orchestrator; the agent triggers `after_agent_turn` upon completion.
- **Conditional Branching**:
    - **Pipeline Loading**: Checks absolute paths first, then project root/pipelines, then validates prompt file existence. If any step fails, returns an empty dict and logs an error.
    - **Session Management**: If `session_id` is empty, a new UUID is generated; otherwise, the existing ID is used to maintain state.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `json`, `uuid`
- **Internal Modules**: 
    - [Functions](/docs/ai/functions.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
    - [LLMConnector](/docs/ai/agents/llm_connector.md)
    - [AgentOrchestrator](/docs/ai/agents/agent_orchestrator.md)
    - [Events](/docs/ai/core/events.md)