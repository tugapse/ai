## 1. Architectural Role
The `ModelOrchestrator` acts as a lifecycle manager for LLM instances, handling the resolution of configuration files, the instantiation of model engines via `EngineManager`, and the synchronization of model parameters.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelOrchestrator` | Class | Orchestrates the loading, switching, and parameter tracking of LLM models. |
| `__init__` | Method | Initializes state for config, LLM instance, parameters, and active model tracking. |
| `load` | Method | Resolves config paths, shuts down existing models, instantiates a new `BaseModel`, and initializes parameters. |
| `_init_model_params` | Method | Extracts `options` from the active LLM into a `ModelParams` dictionary. |
| `get_params` | Method | Returns the current `model_params` dictionary. |
| `get_chat_name` | Method | Returns the `model_chat_name` defined in the loaded JSON config. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig`.
    2. Sets `llm` to `None`.
    3. Initializes `model_params` as an empty dictionary.
    4. Sets `model_chat_name` to `"__no_chat_name__"`.
    5. Sets `active_model_name` to an empty string.
- **Data Path (load)**: 
    `model_config_name` + `system_prompt` $\rightarrow$ Path Resolution $\rightarrow$ `EngineManager.load_config` $\rightarrow$ `EngineManager.load_model_instance` $\rightarrow$ `_init_model_params` $\rightarrow$ `BaseModel` instance.
- **Conditional Branching**:
    - **Filename Normalization**: If `model_config_name` is empty, defaults to `"default.json"`; if it lacks a `.json` extension, it is appended.
    - **Model Switching**: If `model_config_name` differs from `active_model_name`, `self.llm.request_shutdown()` is called if an instance exists.
    - **Path Resolution**: Checks `ProgramSetting.PATHS_MODEL_CONFIGS` in config; if `None`, falls back to `func.get_root_directory()` joined with `"model-config"`.
    - **Error Handling**: Any exception during loading triggers `func.error` with `CRITICAL` level and executes `sys.exit(1)`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `typing` (`Optional`, `Dict`, `Any`)
- **Internal Modules**: `services.model_manager.EngineManager`, `core.llms.base_llm.ModelParams`, `core.llms.base_llm.BaseModel`, `config.ProgramConfig`, `config.ProgramSetting`, `functions` (as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `"default.json"`: Default configuration filename.
    - `".json"`: Required file extension for model configs.
    - `"__no_chat_name__"`: Initial state for `model_chat_name`.
    - `"model-config"`: Fallback directory name.
- **Environment Lookups**: 
    - `ProgramSetting.PATHS_MODEL_CONFIGS`: Used to locate the directory containing model JSON files.