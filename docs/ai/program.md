## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | Program |
| Source file | program.py |

The **Program** class serves as the central nervous system and primary orchestrator for the JARVIS ecosystem. It is responsible for the high-level lifecycle management of the application, including the initialization of core services, the coordination of hardware/software modules, and the management of the user interface. By acting as the glue between disparate subsystems, it ensures that LLM logic, memory, tools, and UI feedback operate in a synchronized manner.

**Functional Mission**
The primary mission of **Program** is to manage the "Autonomous Agent Loop." It solves the problem of complex, multi-step reasoning by implementing a "Thought-Action" cycle that allows the LLM to interact with the real world through tools. It manages the transition from raw user input to structured LLM inference, tool execution, and finally, the persistence of conversation history and memory.

**System Context & Integration**
**Program** sits at the top of the execution hierarchy. It initializes the [ModelOrchestrator](/docs/ai/services/model_orchestrator.md) to handle LLM connectivity and the [ModuleRegistry](/docs/ai/services/module_registry.md) to manage hardware/software plugins. During a chat turn, it utilizes the [StreamOrchestrator](/docs/ai/services/stream_orchestrator.md) to pipe LLM outputs to the [UIOrchestrator](/docs/ai/services/ui_orchestrator.md) and [HistoryManager](/docs/ai/services/history_manager.md). It also acts as a gatekeeper for tool execution via the [ToolRegistry](/docs/ai/tools/tool_registry.md), implementing Human-In-The-Loop (HIL) protocols for sensitive actions.

- **INTERNAL REFERENCES**: 
    - [Chat](/docs/ai/chat/chat.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [ProgramConfig](/docs/ai/config.md)
    - [Agent](/docs/ai/agents/agent.md)
    - [VectorMemoryModule](/docs/ai/modules/vector_memory/vector_memory_module.md)
    - [VectorMemory](/docs/ai/modules/vector_memory/vector_memory.md)
    - [BaseVoiceModule](/docs/ai/modules/voice/base_module.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
    - [AVAILABLE_TOOLS](/docs/ai/tools/agent_tools.md)
    - [SessionManager](/docs/ai/services/session_manager.md)
    - [PromptLoader](/docs/ai/services/prompt_loader.md)
    - [CliConfig](/docs/ai/services/config_helper.md)
    - [EventBinder](/docs/ai/services/event_binder.md)
    - [ModelOrchestrator](/docs/ai/services/model_orchestrator.md)
    - [HistoryManager](/docs/ai/services/history_manager.md)
    - [ModuleRegistry](/docs/ai/services/module_registry.md)
    - [UIOrchestrator](/docs/ai/services/ui_orchestrator.md)
    - [StreamOrchestrator](/docs/ai/services/stream_orchestrator.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `args` (via `load_config`)  CLI arguments used to configure the system and enable specific modules.

**Hardcoded Constants:**
- `MAX_STEPS_BEFORE_WARNING` (Default: `5`)  Threshold for the autonomous loop before a sentinel warning is injected into the chat context.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `__init__` | Method | Initializes core state variables, chat instance, and tool registry. |
| `llm` | Property | Lazy-loader for the active LLM model via `ModelOrchestrator`. |
| `model_params` | Property | Retrieves current model configuration parameters. |
| `load_config` | Method | Loads `ProgramConfig` and initializes core services (Models, History, Modules, UI). |
| `init_program` | Method | Sets up session paths, history, UI, and tool registry. |
| `start_chat` | Method | Entry point for user interaction; triggers the agentic loop. |
| `run` | Method | Starts the main application loop and binds core events. |
| `shutdown` | Method | Performs aggressive cleanup of LLM instances and memory. |
| `route_session` | Method | Switches the active history session to a specific file. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. `load_config` is called to instantiate `ModelOrchestrator`, `HistoryManager`, `ModuleRegistry`, and `UIOrchestrator`.
    2. `init_program` establishes session persistence and loads the `ToolRegistry`.
    3. `_ensure_llm_loaded` is triggered lazily upon first LLM access, loading the system prompt and model.
- **Data Path (The Agentic Loop)**:
    1. **Input**: `start_chat` receives `user_input` $\rightarrow$ added to `HistoryManager`.
    2. **Inference**: `_run_agent_loop` calls `llm.chat` $\rightarrow$ `StreamOrchestrator` processes the stream.
    3. **Decision (Branching)**:
        - **If Tool Call**: `_process_tool_call` $\rightarrow$ checks `HIL_TOOLS` $\rightarrow$ executes via `ToolRegistry` $\rightarrow$ appends result to `Chat` $\rightarrow$ loops back to Inference.
        - **If Text Completion**: `HistoryManager` saves message $\rightarrow$ `VectorMemory` stores turn $\rightarrow$ loop terminates.
        - **If Interrupted**: User signal $\rightarrow$ `llm.request_shutdown()` $\rightarrow$ loop terminates.
- **Conditional Branching**:
    - **HIL Gatekeeper**: If a tool name exists in `llm.HIL_TOOLS`, the system pauses for `input()` confirmation before execution.
    - **Sentinel Warning**: If `step_count` exceeds `MAX_STEPS_BEFORE_WARNING`, a system message is injected to prompt the LLM to summarize and ask for help.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `traceback`, `gc`, `json`, `typing`
- **Internal Modules**: 
    - [Chat](/docs/ai/chat/chat.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [ProgramConfig](/docs/ai/config.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [Color](/docs/ai/color.md)
    - [Agent](/docs/ai/agents/agent.md)
    - [VectorMemoryModule](/docs/ai/modules/vector_memory/vector_memory_module.md)
    - [VectorMemory](/docs/ai/modules/vector_memory/vector_memory.md)
    - [BaseVoiceModule](/docs/ai/modules/voice/base_module.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
    - [AVAILABLE_TOOLS](/docs/ai/tools/agent_tools.md)
    - [load_and_register_user_tools](/docs/ai/tools/tool_loader.md)
    - [SessionManager](/docs/ai/services/session_manager.md)
    - [PromptLoader](/docs/ai/services/prompt_loader.md)
    - [CliConfig](/docs/ai/services/config_helper.md)
    - [EventBinder](/docs/ai/services/event_binder.md)
    - [ModelOrchestrator](/docs/ai/services/model_orchestrator.md)
    - [HistoryManager](/docs/ai/services/history_manager.md)
    - [ModuleRegistry](/docs/ai/services/module_registry.md)
    - [UIOrchestrator](/docs/ai/services/ui_orchestrator.md)
    - [StreamOrchestrator](/docs/ai/services/stream_orchestrator.md)
    - [func](/docs/ai/functions.md)
- **External Packages**: None identified.