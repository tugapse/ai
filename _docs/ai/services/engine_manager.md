## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| EngineManager | ai/services/engine_manager.md |

This component serves as the central orchestration layer for managing the lifecycle of various AI model engines. Its primary responsibility is to abstract the complexity of model loading, configuration validation, and engine instantiation, ensuring that only properly installed and configured models can be utilized by the application. It handles checks against an installed engine status file to prevent runtime failures from unsupported backends.

As a core service within the application, `EngineManager` acts as a factory and validation gatekeeper. It sits between the configuration loading mechanisms (like `load_config` in this file) and the actual model runtime instances (like `BaseModel`). It relies heavily on configuration data and interacts with external systems by checking filesystem presence and dispatching to specific model creation methods based on the model type specified in the configuration.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| is_engine_installed | Static Method | Checks if a specific model or engine type is marked as installed in the system configuration file. |
| generate_default_config | Static Method | Creates a standardized dictionary structure containing default parameters for a given model name and type. |
| load_config | Static Method | Reads and deserializes a JSON file into a configuration dictionary. Raises errors on file not found or invalid JSON. |
| save_config | Static Method | Writes a model configuration dictionary to a specified JSON file path. |
| load_model_instance | Static Method | Validates the model configuration, checks engine installation, and instantiates the correct `BaseModel` subclass. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The core logic revolves around dispatching based on `model_type`. `load_model_instance` first calls `is_engine_installed` to verify prerequisite setup. If valid, it determines the correct private creation method (e.g., `_create_gguf_model`, `_create_openai_model`) and passes the parsed configuration parameters to instantiate the appropriate subclass of `BaseModel`. Configuration generation uses predefined defaults, adjusted slightly based on the `ModelType`.

- **Side Effects:** This component heavily interacts with the filesystem by reading (`load_config`, `is_engine_installed`) and writing (`save_config`) `installed_engines.json` and model configuration files. It also uses `func.log` and `func.error` to interact with logging mechanisms.

- **Error Handling:** It implements robust error handling across its methods. `load_config` specifically catches `json.JSONDecodeError`. `load_model_instance` catches `GpuMemoryError` (allowing the caller to potentially offer alternatives) and raises `ValueError` if the model type is unknown or the engine is not installed.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_ENGINE_STATUS_FILE` — Optional environment variable used to explicitly set the path to the engine status configuration file, overriding default discovery logic.

**Module Dependencies:**
- **Standard/External:** `json`, `os`, `sys`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.entities.model_enums](/ai/entities/model_enums.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.services.process_manager](/ai/services/process_manager.md), [ai.core.llms.load_errors](/ai/core/llms/load_errors.md), [ai.tools.tool_registry](/ai/tools/tool_registry.md), [ai.color](/ai/color.md)