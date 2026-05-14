## 1. Architectural Role
The `Program` class serves as the central orchestrator for the JARVIS system, managing the lifecycle of LLM sessions, tool registry integration, module coordination, and the autonomous agent execution loop.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Program` | Class | Main entry point and system coordinator. |
| `__init__` | Method | Initializes core state variables and empty service containers. |
| `load_config` | Method | Instantiates `ProgramConfig`, `ModelOrchestrator`, `HistoryManager`, `ModuleRegistry`, and `UIOrchestrator`. |
| `init_config` | Method | Applies CLI arguments to configuration and triggers module loading. |
| `init_program` | Method | Sets up session paths, history, UI, and tool registries. |
| `load_tool_registry` | Method | Populates `ToolRegistry` with system, user, and vector memory tools. |
| `start_chat` | Method | Initiates the LLM interaction loop for a specific user input. |
| `_run_agent_loop` | Method | Executes the iterative "Thought-Action" cycle (Inference  Action  Completion). |
| `_process_tool_call` | Method | Executes tools via `tool_registry` with optional Human-In-The-Loop (HIL) gating. |
| `run` | Method | Activates the main execution loop and binds core system events. |
| `shutdown` | Method | Performs aggressive cleanup of LLM instances and memory. |
| `route_session` | Method | Switches the active `HistoryManager` session to a specific file. |
| `llm` | Property | Lazy-loader for the active `BaseModel` instance. |
| `model_params` | Property | Retrieves operational parameters from the loaded model. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` sets default state (e.g., `llm_initialized = False`, `allow_tools = False`).
    2. `load_config` builds the service layer (`models`, `history`, `modules`, `ui`).
    3. `init_program` establishes filesystem persistence and tool availability.
- **Data Path**: 
    `User Input` $\rightarrow$ `history.add_message` $\rightarrow$ `llm.chat` (Stream) $\rightarrow$ `StreamOrchestrator.run` $\rightarrow$ `stream_result` $\rightarrow$ (If Tool Call) $\rightarrow$ `tool_registry.execute_tool` $\rightarrow$ `history.add_message` (Tool Result) $\rightarrow$ `llm.chat` (Loop) $\rightarrow$ `stream_result.accumulated_text` $\rightarrow$ `history.add_message` (Final Response) $\rightarrow$ `vector_memory.add_memory`.
- **Conditional Branching**:
    - **Tool Execution**: Checks if tool name exists in `llm.HIL_TOOLS`; if true, triggers `_request_human_permission` (blocking input).
    - **Agent Loop Termination**: Continues while `stream_result.tool_calls` is populated; breaks when `stream_result.accumulated_text` is present or `stream_result.interrupted` is true.
    - **Sentinel Warning**: If `step_count` exceeds `MAX_STEPS_BEFORE_WARNING` (5), injects a system prompt warning into the chat history.
    - **LLM Loading**: Uses `llm_initialized` flag to decide between lazy-loading a new `ModelOrchestrator` or updating the existing `system_prompt`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `traceback`, `gc`, `json`, `typing`
- **Internal Modules**: `chat.chat`, `core.llms.base_llm`, `config`, `color`, `agents.agent`, `modules.memory.vector_memory_module`, `modules.memory.vector_memory`, `tools.tool_registry`, `tools.agent_tools`, `tools.tool_loader`, `services.session_manager`, `services.prompt_loader`, `services.config_helper`, `services.event_binder`, `services.model_orchestrator`, `services.history_manager`, `services.module_registry`, `services.ui_orchestrator`, `services.stream_orchestrator`, `functions`
- **External Packages**: N/A (Relies on internal implementations of `Color` and `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `MAX_STEPS_BEFORE_WARNING = 5`
- **Environment Lookups**: 
    - `ProgramSetting.SYSTEM_PROMPT_FILE` (via `config`)
    - `ProgramSetting.MODEL_CONFIG_NAME` (via `config`)
    - `func.get_root_directory()` (used for tool path resolution)