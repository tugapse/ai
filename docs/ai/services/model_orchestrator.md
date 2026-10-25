## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ModelOrchestrator |
| Source file | model_orchestrator.py |

The **ModelOrchestrator** serves as the high-level controller for managing the lifecycle of Large Language Model (LLM) instances within the application. It acts as a bridge between configuration data and the actual execution engines, ensuring that the correct model is loaded, initialized with appropriate system prompts, and equipped with the necessary toolsets.

**Functional Mission**
The primary responsibility of **ModelOrchestrator** is to abstract the complexity of model instantiation and state management. It solves the problem of dynamic model switching by handling the graceful shutdown of existing LLM instances and the loading of new configurations, ensuring that the system's active model state remains consistent with the requested configuration.

**System Context & Integration**
This component sits between the high-level application logic and the low-level engine management. It utilizes [EngineManager](/docs/ai/services/engine_manager.md) to perform the heavy lifting of model loading and instance creation. It integrates with [ToolRegistry](/docs/ai/tools/tool_registry.md) to inject capabilities into the model and relies on [ProgramConfig](/docs/ai/services/config_helper.md) to resolve file system paths for model configurations. When a model is successfully loaded, it provides a [BaseModel](/docs/ai/core/llms/base_llm.md) instance to the caller, effectively transitioning the system from a configuration state to an active execution state.

## 2. Environment & Configuration
**Environment Lookups:**
- `PATHS_MODEL_CONFIGS` (via `self.config.get`)  Retrieves the directory path where model JSON configuration files are stored.

**Hardcoded Constants:**
- `__no_chat_name__` (Default: `"__no_chat_name__"`)  Initial placeholder for the model's chat identifier.
- `default.json` (Default: `"default.json"`)  Fallback filename if no specific model configuration name is provided.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `__init__` | Class Method | Initializes the orchestrator with a `ProgramConfig` and sets default empty states. |
| `load` | Method | Orchestrates the loading process: resolves config paths, shuts down old models, and instantiates new ones via `EngineManager`. |
| `_init_model_params` | Method | Internal helper to extract and convert model-specific options into a dictionary format using `ModelParams`. |
| `get_params` | Method | Returns the current dictionary of model parameters/options. |
| `get_chat_name` | Method | Returns the human-readable name of the currently active model. |

## 4. Execution Logic & Flow
- **Initialization**: The orchestrator is instantiated with a `ProgramConfig`. It sets `active_model_name` to an empty string, `llm` to `None`, and initializes an empty `model_params` dictionary.
- **Data Path (Model Loading)**:
    1. **Input**: Receives `model_config_name`, `system_prompt`, optional `tool_registry`, and optional `model_config_data`.
    2. **Resolution**: If `model_config_data` is missing, it resolves the file path using `PATHS_MODEL_CONFIGS` from the config. It ensures the filename ends with `.json`.
    3. **Cleanup**: If the requested model differs from `active_model_name`, it calls `request_shutdown()` on the existing `llm` instance.
    4. **Instantiation**: Calls `EngineManager.load_model_instance` with the resolved configuration and prompt.
    5. **Parameter Mapping**: Calls `_init_model_params` to transform the model's `options` attribute into a serializable dictionary.
    6. **Output**: Returns the instantiated `BaseModel` object.
- **Conditional Branching**:
    - **Config Override**: If `model_config_data` contains `"model_name"`, it overrides the `model_config_name` argument.
    - **Path Fallback**: If `PATHS_MODEL_CONFIGS` is missing, it falls back to a `models` folder in the root directory (via `func.get_root_directory()`).
    - **Error Handling**: Any failure in loading the config or the model instance triggers a `CRITICAL` error via `func.error` and terminates the process via `sys.exit(1)`.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [EngineManager](/docs/ai/services/engine_manager.md)
    - [ModelParams](/docs/ai/core/llms/base_llm.md)
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
- **External Packages**: None identified.