## 1. Architectural Role
The `EngineManager` class serves as a centralized factory and configuration handler responsible for validating engine availability, managing JSON-based model configurations, and orchestrating the instantiation of specific LLM subclasses.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `is_engine_installed` | Static Method | Validates if a specific `ModelType` or `EngineType` is marked as "installed" within the `installed_engines.json` configuration file. |
| `generate_default_config` | Static Method | Constructs a standardized dictionary containing default hyperparameters and metadata for a new model configuration. |
| `load_config` | Static Method | Reads and parses a JSON file from a provided path into a dictionary, including error handling for missing files or invalid JSON. |
| `save_config` | Static Method | Serializes a configuration dictionary into a JSON file at the specified path. |
| `load_model_instance` | Static Method | Performs the primary orchestration: validates engine status, parses parameters, and returns a concrete implementation of `BaseModel`. |

## 3. Execution Logic & Flow
- **Initialization**: No instance state is maintained; the class operates entirely through static methods.
- **Data Path**: 
    - **Config Path**: `filepath` (str) $\rightarrow$ `json.load` $\rightarrow$ `dict` (model_config).
    - **Instantiation Path**: `model_config` (dict) $\rightarrow$ `ModelType` validation $\rightarrow$ `is_engine_installed` check $\rightarrow$ `ModelParams` conversion $\rightarrow$ Subclass-specific kwargs filtering $\rightarrow$ `BaseModel` instance.
- **Conditional Branching**:
    - **Engine Validation**: Checks `mapping` dictionary; applies special logic for `ModelType.GEMINI` if `vertex` is in `module_name`.
    - **Model Type Dispatch**: 
        - `ModelType.CAUSAL_LM` $\rightarrow$ `HuggingFaceModel`.
        - `ModelType.OLLAMA` $\rightarrow$ `OllamaModel`.
        - `ModelType.GGUF` $\rightarrow$ `GGUFImageLLM` (includes `llama_cpp` logging override).
        - `ModelType.GEMINI` $\rightarrow$ `GeminiAPIModel`.
        - `ModelType.OPEN_AI` $\rightarrow$ `OpenAIAPIModel`.
    - **Parameter Filtering**: Removes specific keys (`quantization_bits`, `n_ctx`, etc.) from `model_properties` before passing them as `**other_llm_kwargs`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `os`, `sys`, `typing` (Optional, Union), `ctypes`.
- **Internal Modules**: `functions` (as `func`), `entities.model_enums` (`ModelType`, `EngineType`), `core.llms.base_llm` (`ModelParams`, `BaseModel`), `tools.tool_registry` (`ToolRegistry`).
- **External Packages**: `llama_cpp`, `color`.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `mapping` (Enum to JSON ID mapping).
    - Default `model_properties` (max_new_tokens: 1024, temperature: 0.7, etc.).
    - `root_dir` calculation via `os.path.join` (stepping up three levels from `src/ai/services/`).
- **Environment Lookups**: 
    - `installed_engines.json` (Project root level).
    - `model_config` dictionary keys: `model_name`, `model_type`, `model_properties`, `gguf_filename`, `model_repo_id`, `n_ctx`, `n_gpu_layers`, `vertex_ai`.