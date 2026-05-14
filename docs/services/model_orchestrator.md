## 1. Architectural Role
Manages the lifecycle, configuration loading, and instantiation of LLM engine instances through a centralized orchestration interface.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelOrchestrator` | Class | Orchestrates LLM loading, parameter synchronization, and model instance management. |
| `__init__` | Method | Initializes the orchestrator state with provided program configuration. |
| `load` | Method | Resolves model configuration paths, shuts down existing models, and instantiates a new `BaseModel`. |
| `_init_model_params` | Method | Synchronizes internal `model_params` dictionary with the active LLM's options. |
| `get_params` | Method | Returns the current dictionary of model parameters. |
| `get_chat_name` | Method | Returns the identifier string for the currently loaded model. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Sets `config` from `ProgramConfig`.
    - Initializes `model_params` as an empty dictionary.
    - Sets `model_chat_name` to `"__no_chat_name__"`.
    - Sets `active_model_name` to an empty string.
    - Sets `llm` to `None`.
- **Data Path**: 
    - `model_config_name` (String) $\rightarrow$ Path Resolution (via `ProgramSetting.PATHS_MODEL_CONFIGS` or `func.get_root_directory()`) $\rightarrow$ `EngineManager.load_config` (Dict) $\rightarrow$ `EngineManager.load_model_instance` (`BaseModel`) $\rightarrow$ `_init_model_params` (Dict) $\rightarrow$ `self.llm`.
- **Conditional Branching**:
    - **Filename Validation**: If `model_config_name` does not end in `.json`, appends `.json`.
    - **State Management**: If the requested `model_config_name` differs from `active_model_name`, triggers `self.llm.request_shutdown()` if a model is currently active.
    - **Path Fallback**: If `self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)` returns `None`, defaults to `os.path.join(func.get_root_directory(), "model-config")`.
    - **Parameter Mapping**: If `self.llm` has an `options` attribute, maps `ModelParams(**self.llm.options)` to a dictionary; otherwise, initializes default `ModelParams`.
    - **Error Handling**: If `EngineManager.load_model_instance` returns `None` or an exception occurs, logs a `CRITICAL` error via `func.error` and terminates the process via `sys.exit(1)`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `typing`
- **Internal Modules**: `services.engine_manager`, `core.llms.base_llm`, `services.config_helper`, `functions`, `tools.tool_registry`
- **External Packages**: None explicitly imported (relies on internal abstraction)

## 5. Configuration & Environment
- **Hardcoded Constants**: `"default.json"`, `"__no_chat_name__"`, `"model-config"`.
- **Environment Lookups**: `ProgramSetting.PATHS_MODEL_CONFIGS` (via `self.config`).