## 1. Architectural Role
The `Program` class acts as the central nervous system and primary orchestrator for the JARVIS ecosystem. It manages the lifecycle of all major subsystems, including the [ModelOrchestrator](services/model_orchestrator.md) for LLM management, the [ModuleRegistry](services/module_registry.md) for hardware/software components, and the [StreamOrchestrator](services/stream_orchestrator.md) for handling real-time inference and tool execution. It bridges the gap between user input via [Chat](chat/chat.md), persistent storage through [HistoryManager](services/history_manager.md), and agentic reasoning via [Agent](agents/agent.md), ensuring that tool calls, memory injection into [VectorMemory](modules/memory/vector_memory.md), and UI updates are synchronized.

## 2. Environment & Configuration
**Environment Lookups:**
- `args` (via `load_config`)  CLI arguments passed to initialize the system state.
- `args.modules` (via `init_config`)  List of specific modules to enable via CLI.

**Hardcoded Constants:**
- `MAX_STEP_BEFORE_WARNING` (Default: `5`)  Threshold for injecting sentinel warnings into the autonomous agent loop.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Program` | Class | The main entry point and orchestrator for the entire application. |
| `load_config` | Method | Loads the [ProgramConfig](config.md) and initializes core service managers. |
| `init_config` | Method | Applies CLI overrides to the configuration and triggers module loading. |
| `init_program` | Method | Sets up session paths, history, UI, and the tool registry. |
| `load_tool_registry` | Method | Populates the [ToolRegistry](tools/tool_registry.md) with system, user, and memory-derived tools. |
| `start_chat` | Method | The primary entry point for a single interaction turn, managing the agent loop. |
| `_run_agent_loop` | Method | Manages the iterative "Thought-Action-Observation" cycle of the LLM. |
| `_process_tool_call` | Method | Executes requested tools and enforces Human-In-The-Loop (HIL) permissions. |
| `run` | Method | Starts the main [Chat](chat/chat.md) loop and binds core events via [EventBinder](services/event_binder.md). |
| `shutdown` | Method | Performs a graceful, aggressive cleanup of LLM instances and modules. |
| `route_session` | Method | Switches the active history session to a different file path. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. `load_config` creates service instances ([ModelOrchestrator](services/model_orchestrator.md), [HistoryManager](services/history_manager.md), etc.).
    2. `init_config` applies CLI arguments to the [ProgramConfig](config.md).
    3. `init_program` sets up [SessionManager](services/session_manager.md) paths and [UIOrchestrator](services/ui_orchestrator.md).
    4. `load_tool_registry` pulls tools from [AVAILABLE_TOOLS](tools/agent_tools.md), user directories, and [VectorMemoryModule](modules/memory/vector_memory_module.md).
- **Data Path**:
    1. `User Input` $\rightarrow$ `Chat.add_message` $\rightarrow$ `llm.chat(stream=True)`.
    2. `Stream` $\rightarrow$ `StreamOrchestrator.run()` $\rightarrow$ `stream_result`.
    3. If `tool_calls` present $\rightarrow$ `_process_tool_call` $\rightarrow$ `ToolRegistry.execute_tool` $\rightarrow$ `Chat.messages` (updated with tool result).
    4. If `accumulated_text` present $\rightarrow$ `HistoryManager.add_message` $\rightarrow$ `VectorMemory.add_memory`.
- **Conditional Branching**:
    - **HIL Gatekeeper**: If a tool name is in `llm.HI_TOOLS`, execution halts for `_request_human_permission`.
    - **Agent Loop Termination**: The loop breaks if the LLM produces `accumulated_text` (Completion) or if the user interrupts the stream.
    - **Sentinel Warning**: If `step_count > MAX_STEPS_BEFORE_WARNING`, a system message is injected into the chat history to redirect the LLM.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `traceback`, `gc`, `json`, `typing`
- **Internal Modules**: 
    - [chat/chat.md](chat/chat.md)
    - [core/llms/base_llm.md](core/llms/base_llm.md)
    - [config.md](config.md)
    - [color.md](color.md)
    - [agents/agent.md](agents/agent.md)
    - [modules/memory/vector_memory_module.md](modules/memory/vector_memory_module.md)
    - [modules/memory/vector_memory.md](modules/memory/vector_memory.md)
    - [tools/tool_registry.md](tools/tool_registry.md)
    - [tools/agent_tools.md](tools/agent_tools.md)
    - [tools/tool_loader.md](tools/tool_loader.md)
    - [services/session_manager.md](services/session_manager.md)
    - [services/prompt_loader.md](services/prompt_loader.md)
    - [services/config_helper.md](services/config_helper.md)
    - [services/event_binder.md](services/event_binder.md)
    - [services/model_orchestrator.md](services/model_orchestrator.md)
    - [services/history_manager.md](services/history_manager.md)
    - [services/module_registry.md](services/module_registry.md)
    - [services/ui_orchestrator.md](services/ui_orchestrator.md)
    - [services/stream_orchestrator.md](services/stream_orchestrator.md)
    - [functions.md](functions.md)
- **External Packages**: None identified in imports (standard library usage only).