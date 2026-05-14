## 1. Architectural Role
The `ModelOrchestrator` class serves as the lifecycle manager and factory interface for Large Language Model (LLM) instances. It abstracts the complexity of loading specific model configurations, managing model-specific parameters, and handling the graceful shutdown of existing instances when switching models. It acts as a bridge between high-level configuration settings via [services/config_helper.md](services/config_helper.md) and the underlying execution engines managed by [services/engine_manager.md](services/engine_manager.md), ensuring that the active [core/llms/base_llm.md](core/llms/base_llm.md) is correctly initialized with system prompts and toolsets.

## 2. Environment & Configuration
**Environment Lookups:**
- `PATHS_MODEL_CONFIGS` (via `ProgramConfig`)  Locates the directory containing JSON model definition files.

**Hardcoded Constants:**
- `__no_chat_name__` (Default: `"__no_chat_name__"`)  Initial state for the chat name identifier before a model is loaded.
- `default.json` (Default: `"default.json"`)  Fallback filename if no model configuration name is provided.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelOrchestrator` | Class | Manages the loading, parameter tracking, and lifecycle of LLM instances. |
| `__init__` | Method | Initializes the orchestrator with a `ProgramConfig` and sets default empty states. |
| `load` | Method | Orchestrates the transition to a new model: shuts down existing LLMs, resolves file paths, invokes the engine manager, and initializes parameters. |
| `_init_model_params` | Method | Extracts and transforms model-specific options into a dictionary format via `ModelParams`. |
| `get_params` | Method | Returns the current dictionary of model parameters. |
| `get_chat_name` | Method | Returns the name associated with the currently loaded model configuration. |

## 4. Execution Logic & Flow
- **Initialization**:
    - Receives `ProgramConfig`.
    - Sets `model_params` to empty dict, `model_chat_name` to `"__no_chat_name__"`, and `llm` to `None`.
- **Data Path (Model Loading)**:
    1. **Input**: `model_config_name` (string), `system_prompt` (string), `tool_registry` (Optional).
    2. **Path Resolution**: Validates extension; if missing, appends `.json`. Fetches directory from `ProgramConfig`. Falls back to `functions.get_root_directory()` + `/model-config` if path is null.
    3. **State Management**: If a model is already active, calls `self.llm.request_shutdown()`.
    4. **Engine Invocation**: Calls `EngineManager.load_config(filename)` followed by `EngineManager.load_model_instance(...)`.
    5. **Parameter Sync**: Calls `_init_model_params` to map `llm.options` to `ModelParams`.
    6. **Output**: Returns an instance of `BaseModel`.
- **Conditional Branching**:
    - **File Extension Check**: Appends `.json` if the input name lacks it.
    - **Model Switch Check**: Only triggers shutdown if `model_config_name` differs from `active_model_name`.
    - **Configuration Path Fallback**: If `PATHS_MODEL_CONFIGS` is `None`, it uses a local project root path.
    - **Error Handling**: Any failure during the loading sequence triggers a critical error log via `functions.error` and terminates the process via `sys.exit(1)`.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `typing`
- **Internal Modules**: 
    - [services/engine_manager.md](services/engine_manager.md)
    - [core/llms/base_llm.md](core/llms/base_llm.md)
    - [services/config_helper.md](services/config_helper.md)
    - [functions.md](functions.md)
    - [tools/tool_registry.md](tools/tool_registry.md)
- **External Packages**: None identified.