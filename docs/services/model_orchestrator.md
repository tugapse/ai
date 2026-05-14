## 1. Architectural Role

**Functional Mission**
The **ModelOrchestrator** serves as the centralized lifecycle manager for Large Language Model (LLM) instances within the application. Its primary mission is to abstract the complexities of model loading, configuration parsing, and resource management, providing a unified interface to switch between different model backends while ensuring that previous model instances are gracefully decommissioned to prevent resource leaks.

**System Context & Integration**
This component acts as a high-level controller that bridges configuration data and active execution engines. It utilizes [EngineManager](/docs/services/engine_manager.md) to instantiate specific [BaseModel](/docs/core/llms/base_llm.md) implementations based on JSON configuration files. By managing the `active_model_name` and handling the transition between models, it provides a stable state for downstream servicessuch as chat managers or agentic loopsto interact with a consistent LLM interface without needing to manage the underlying engine's lifecycle or parameter initialization.

## 2. Environment & Configuration

**Environment Lookups:**
- `PATHS_MODEL_CONFIGS` (via `self.config.get`)  Retrieves the directory path where model JSON configuration files are stored.

**Hardcoded Constants:**
- `__no_chat_name__` (Default: `"__no_chat_name__"`)  Initial placeholder for the model's chat identifier.
- `default.json` (Default: `"default.json"`)  Fallback filename if no specific model configuration is provided.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelOrchestrator` | Class | Orchestrates the loading, lifecycle, and parameter management of LLM instances. |
| `__init__` | Method | Initializes the orchestrator with a `ProgramConfig` and sets default empty states. |
| `load` | Method | Performs the heavy lifting of loading a model: validates paths, shuts down existing models, invokes the engine manager, and initializes parameters. |
| `_init_model_params` | Method | Synchronizes the internal `model_params` dictionary with the attributes of the currently loaded LLM instance. |
| `get_params` | Method | Returns the current model's operational parameters as a dictionary. |
| `get_chat_name` | Method | Returns the human-readable name associated with the currently loaded model. |

## 4. Execution Logic & Flow

- **Initialization**: 
    - Accepts `ProgramConfig`.
    - Sets `model_params` to an empty dictionary.
    - Sets `model_chat_name` to `__no_chat_name__`.
    - Sets `active_model_name` to an empty string and `llm` to `None`.
- **Data Path (Model Loading)**:
    1. **Input**: `model_config_name` (string), `system_prompt` (string), `tool_registry` (optional).
    2. **Path Normalization**: Appends `.json` if missing; resolves the directory path using `ProgramSetting.PATHS_MODEL_CONFIGS` or a fallback root directory.
    3. **Lifecycle Check**: If the requested model differs from `active_model_name`, the current `llm.request_shutdown()` is called.
    4. **Instantiation**: `EngineManager.load_config` reads the file; `EngineManager.load_model_instance` creates the LLM object.
    5. **Parameter Sync**: `_init_model_params` extracts `options` from the LLM and converts them to a dictionary via `ModelParams`.
    6. **Output**: Returns the initialized `BaseModel` instance.
- **Conditional Branching**:
    - **Config Path Missing**: If `PATHS_MODEL_CONFIGS` is null, it falls back to a `model-config` folder in the project root.
    - **Model Load Failure**: If `EngineManager` returns `None` or an exception occurs during loading, the error is logged via `func.error` and the process terminates via `sys.exit(1)`.
    - **Parameter Availability**: If the LLM lacks an `options` attribute, `model_params` defaults to an empty `ModelParams` dictionary.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `sys`, `typing`
- **Internal Modules**: 
    - [EngineManager](/docs/services/engine_manager.md)
    - [ModelParams](/docs/core/llms/base_llm.md)
    - [BaseModel](/docs/core/llms/base_llm.md)
    - [ProgramConfig](/docs/services/config_helper.md)
    - [ProgramSetting](/docs/services/config_helper.md)
    - [functions](/docs/functions.md)
    - [ToolRegistry](/docs/tools/tool_registry.md)
- **External Packages**: None identified.