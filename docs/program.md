## 1. Architectural Role
The `Program` class serves as the central system orchestrator, coordinating the lifecycle of LLM instances, session persistence, hardware module registration, and the execution flow between user input and UI feedback.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Program` | Class | Main coordinator for JARVIS services and state. |
| `llm` | Property | Lazy-loader and setter for the active LLM instance. |
| `model_params` | Property | Retrieves current LLM parameters after ensuring initialization. |
| `load_config` | Method | Instantiates core service managers (`ModelOrchestrator`, `HistoryManager`, etc.). |
| `init_program` | Method | Applies CLI arguments, initializes session paths, and loads modules. |
| `_ensure_llm_loaded` | Method | Internal trigger to load the LLM and system prompt from config. |
| `_handle_tool_call` | Method | Processes tool execution confirmation and restarts the chat loop. |
| `start_chat` | Method | Manages a single interaction turn: input processing $\rightarrow$ streaming $\rightarrow$ history update. |
| `run` | Method | Binds core events and enters the main `chat.loop()`. |
| `shutdown` | Method | Performs safety cleanup and requests LLM shutdown. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `__init__` sets initial state flags (`llm_initialized = False`) and initializes an empty `Chat` object.
    2. `load_config` creates service instances based on `ProgramConfig`.
    3. `init_program` modifies config via `ConfigApplier`, sets up `SessionManager` paths, and triggers `ModuleRegistry.load_all()`.
- **Data Path**: 
    `user_input` $\rightarrow$ `HistoryManager` (add message) $\rightarrow$ `ModelOrchestrator` (via `llm` property) $\rightarrow$ `StreamOrchestrator` (processing stream) $\rightarrow$ `UIOrchestrator` (printing/formatting) $\rightarrow$ `HistoryManager` (save result).
- **Conditional Branching**:
    - **Lazy Loading**: Accessing `self.llm` or `self.model_params` triggers `_ensure_llm_loaded` if `llm_initialized` is `False`.
    - **Stream Interruption**: If `stream_result.interrupted` is true, the system calls `llm.request_shutdown()` and logs a user interruption.
    - **Client Mode**: The `llm.setter` allows external injection of a remote LLM, bypassing local loading.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `traceback`, `typing.Optional`
- **Internal Modules**: 
    - `core.chat.Chat`, `core.chat.ChatRoles`
    - `core.llms.base_llm.BaseModel`
    - `config.ProgramConfig`, `config.ProgramSetting`
    - `services.session_manager.SessionManager`
    - `services.prompt_loader.PromptLoader`
    - `services.config_applier.ConfigApplier`
    - `services.event_binder.EventBinder`
    - `services.model_orchestrator.ModelOrchestrator`
    - `services.history_manager.HistoryManager`
    - `services.module_registry.ModuleRegistry`
    - `services.ui_orchestrator.UIOrchestrator`
    - `services.stream_orchestrator.StreamOrchestrator`
    - `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: 
    - `ProgramSetting.SYSTEM_PROMPT_FILE`: Used to locate the system prompt file.
    - `ProgramSetting.MODEL_CONFIG_NAME`: Used to identify which model configuration to load.