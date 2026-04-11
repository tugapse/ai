

## 1. Architectural Role  
Main orchestrator for JARVIS, coordinating services to handle LLM logic, hardware modules, UI feedback, and session persistence.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `Program` | Class | Central coordinator for initializing and managing services, chat flow, and hardware modules. |  
| `load_config` | Method | Loads configuration and initializes core services (models, history, modules, UI). |  
| `init_program` | Method | Applies CLI arguments to config, initializes session paths, loads system prompt, and starts modules. |  
| `start_chat` | Method | Executes one interaction turn with LLM, handles UI components, and processes chat responses. |  
| `run` | Method | Binds core events and starts the main chat loop, handling shutdown and resource cleanup. |  
| `llm` | Property | Provides access to the active LLM model via `ModelOrchestrator`. |  
| `model_params` | Property | Returns model-specific parameters for configuration. |  
| `_handle_tool_call` | Method | Processes tool calls by adding to history and triggering UI updates. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `config`, `models`, `history`, `modules`, `ui`, and `chat` attributes; initializes `clear_on_init`, `write_to_file`, and `output_filename` flags.  
- **Data Path**: User input  `history.add_message(ChatRoles.USER, user_input)`  LLM processing via `self.llm.chat`  `StreamOrchestrator` transforms stream output  `history.add_message(ChatRoles.ASSISTANT, ...)`  UI updates via `ui_tools["printer"]`.  
- **Conditional Branching**:  
  - Checks if `self.llm` exists before processing.  
  - Catches exceptions during chat execution and logs critical errors.  
  - Executes final cleanup for voice modules and saves history post-chat.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `sys`, `traceback`.  
- **Internal Modules**: `core.chat`, `core.llms.base_llm`, `config`, `services.session_manager`, `services.prompt_loader`, `services.config_applier`, `services.model_orchestrator`, `services.history_manager`, `services.module_registry`, `services.ui_orchestrator`, `services.stream_orchestrator`.  
- **External Packages**: None explicitly referenced.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `ProgramSetting.SYSTEM_PROMPT_FILE`, `ProgramSetting.MODEL_CONFIG_NAME`.  
- **Environment Lookups**: `ConfigApplier.apply_cli_args_to_config` accesses CLI arguments; `SessionManager.initialize_session_paths` uses config values for session paths.