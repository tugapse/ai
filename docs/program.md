## 1. Architectural Role

**Functional Mission**
The **Program** class serves as the central nervous system and primary orchestrator for the JARVIS ecosystem. Its core mission is to synchronize disparate servicesincluding LLM management, tool execution, memory retrieval, and UI feedbackinto a cohesive, autonomous agentic loop. It solves the problem of complex state management by acting as the single point of truth for session persistence, hardware module activation, and the "Thought-Action" cycle required for agentic reasoning.

**System Context & Integration**
As the top-level controller, **Program** integrates the [Chat](/docs/chat/chat.md) state with the [ModelOrchestrator](/docs/services/model_orchestrator.md) to drive intelligence. It manages the lifecycle of the [Agent](/docs/agents/agent.md) and coordinates the [StreamOrchestrator](/docs/services/stream_orchestrator.md) to handle real-time LLM outputs. Data flows from user input through the [HistoryManager](/docs/services/history_manager.md) and into the LLM, while tool-based actions are routed through the [ToolRegistry](/docs/tools/tool_registry.md). It also serves as the bridge between high-level logic and low-level services like the [UIOrchestrator](/docs/services/ui_orchestrator.md) and [SessionManager](/docs/services/session_manager.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `args` (via `load_config`)  CLI arguments used to initialize system configuration.
- `args.modules` (via `init_config`)  List of specific modules to enable via command line.

**Hardcoded Constants:**
- `MAX_STEPS_BEFORE_WARNING` (Default: `5`)  Threshold for injecting a sentinel warning into the LLM context to prevent infinite loops.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Program` | Class | The main orchestrator managing the lifecycle of the entire application. |
| `load_config` | Method | Loads `ProgramConfig` and initializes core services (Models, History, Modules, UI). |
| `init_config` | Method | Applies CLI overrides to the configuration and triggers module loading. |
| `init_program` | Method | Sets up session paths, history, UI, and the tool registry. |
| `load_tool_registry` | Method | Populates the registry with system, user, and vector-memory-derived tools. |
| `start_chat` | Method | The entry point for a user interaction turn; manages the agentic loop. |
| `_run_agent_loop` | Method | Executes the iterative "Thought-Action" cycle (Inference $\rightarrow$ Tool Call $\rightarrow$ Completion). |
| `_process_tool_call` | Method | Executes requested tools and manages Human-In-The-Loop (HIL) permission gates. |
| `run` | Method | Starts the main event loop and binds core system events. |
| `shutdown` | Method | Performs aggressive resource cleanup, including LLM shutdown and garbage collection. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. `load_config` instantiates the `ModelOrchestrator`, `HistoryManager`, `ModuleRegistry`, and `UIOrchestrator`.
    2. `init_program` establishes session persistence via `SessionManager`.
    3. `load_tool_registry` aggregates tools from `AVAILABLE_TOOLS`, local directories, and `VectorMemoryModule`.
- **Data Path**: 
    1. **Input**: `user_input` is received via `start_chat` and appended to `Chat` history.
    2. **Inference**: `llm.chat` generates a stream; `StreamOrchestrator` processes the stream.
    3. **Action**: If `tool_calls` are detected, `_process_tool_call` executes the tool via `ToolRegistry`.
    4. **Feedback**: Tool results are appended to `Chat` messages as `tool` roles.
    5. **Loop**: The cycle repeats until `accumulated_text` is received (Completion) or the user interrupts.
    6. **Memory**: Final text is sent to `VectorMemory` for long-term storage.
- **Conditional Branching**:
    - **HIL Gate**: If a tool name exists in `llm.HIL_TOOLS`, execution pauses for `_request_human_permission`.
    - **Sentinel Check**: If `step_count` exceeds `MAX_STEPS_BEFORE_WARNING`, a system warning is injected into the chat context.
    - **Interruption**: If `stream_result.interrupted` is true, the loop breaks and the LLM is signaled to shut down.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `traceback`, `gc`, `json`, `typing`
- **Internal Modules**: 
    - [Chat](/docs/chat/chat.md)
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [ProgramConfig](/docs/config.md)
    - [Agent](/docs/agents/agent.md)
    - [VectorMemoryModule](/docs/modules/memory/vector_memory_module.md)
    - [VectorMemory](/docs/modules/memory/vector_memory.md)
    - [ToolRegistry](/docs/tools/tool_registry.md)
    - [AVAILABLE_TOOLS](/docs/tools/agent_tools.md)
    - [load_and_register_user_tools](/docs/tools/tool_loader.md)
    - [SessionManager](/docs/services/session_manager.md)
    - [PromptLoader](/docs/services/prompt_loader.md)
    - [CliConfig](/docs/services/config_helper.md)
    - [EventBinder](/docs/services/event_binder.md)
    - [ModelOrchestrator](/docs/services/model_orchestrator.md)
    - [HistoryManager](/docs/services/history_manager.md)
    - [ModuleRegistry](/docs/services/module_registry.md)
    - [UIOrchestrator](/docs/services/ui_orchestrator.md)
    - [StreamOrchestrator](/docs/services/stream_orchestrator.md)
    - [functions](/docs/functions.md)
    - [Color](/docs/color.md)
- **External Packages**: None identified.