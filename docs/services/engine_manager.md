## 1. Architectural Role
The [engine_manager.py](src/ai/services/engine_manager.py) serves as the factory and lifecycle controller for Large Language Model (LLM) instances. It is responsible for verifying the presence of required backend engines via local configuration files, generating standardized model parameter templates, and performing the late-binding instantiation of specific model implementations from [core/llms/base_llm.md](core/llms/base_llm.md) subclasses. It acts as a critical bridge between static JSON configurations and active runtime model objects.

## 2. Environment & Configuration
**Environment Lookups:**
- `installed_engines.json` (via `is_engine_installed`)  Validates if the specific backend (e.g., Ollama, OpenAI, GGuf) is configured and installed on the host system.

**Hardcoded Constants:**
- `mapping` (Default: `dict`)  Maps [entities/model_enums.md](entities/model_enums.md) (`ModelType`, `EngineType`) to specific JSON keys for engine verification.
- `max_new_tokens` (Default: `1024`)  Default generation limit in `generate_default_config`.
- `temperature` (Default: `0.7` / `0.9`)  Default sampling randomness, adjusted for `SEQ2SEQ_LM`.
- `top_p` (Default: `0.95` / `0.9`)  Default nucleus sampling threshold.
- `top_k` (Default: `50`)  Default top-k sampling threshold.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EngineManager` | Class | Static utility container for model lifecycle operations. |
| `is_engine_installed` | Static Method | Performs environment audits by checking `installed_engines.json`. |
| `generate_default_config` | Static Method | Produces a structured dictionary for new model initialization. |
| `load_config` | Static Method | Deserializes JSON configuration files with error handling. |
| `save_config` | Static Method | Serializes configuration dictionaries to JSON files. |
| `load_model_instance` | Static Method | The primary factory method; instantiates specific [core/llms/base_llm.md](core/llms/base_llm.md) implementations. |

## 4. Execution Logic & Flow
- **Initialization**: The class is stateless; logic is invoked via static methods.
- **Data Path**: 
    1. **Input**: `model_config` (dict) + `system_prompt` (str) + `tool_registry` (obj).
    2. **Processing**: 
        - Validate existence of `model_name` and `model_type`.
        - Cast `model_type` using [entities/model_enums.md](entities/model_enums.md).
        - Verify backend engine status via `is_engine_installed`.
        - Transform `model_properties` into `ModelParams` and filter `other_llm_kwargs`.
        - Execute conditional lazy-imports for specific model classes.
    3. **Output**: A concrete instance of a subclass of [core/llms/base_llm.md](core/llms/base_llm.md).
- **Conditional Branching**:
    - **Engine Check**: If `is_engine_installed` returns `False`, raises `ValueError`.
    - **Type Dispatch**: 
        - `CAUSAL_LM` $\rightarrow$ [core/llms/huggingface_model.md](core/llms/huggingface_model.md)
        - `OLLAMA` $\rightarrow$ [core/llms/ollama_model.md](core/llms/ollama_model.md)
        - `GGUF` $\rightarrow$ [core/llms/gguf_model.md](core/llms/gguf_model.md) (includes `llama-cpp` logging override)
        - `GEMINI` $\rightarrow$ [core/llms/gemini.md](core/llms/gemini.md)
        - `OPEN_AI` $\rightarrow$ [core/llms/open_ai.md](core/llms/open_ai.md)

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `os`, `sys`, `typing`, `ctypes`
- **Internal Modules**: 
    - [functions.md](functions.md)
    - [entities/model_enums.md](entities/model_enums.md)
    - [core/llms/base_llm.md](core/llms/base_llm.md)
    - [tools/tool_registry.md](tools/tool_registry.md)
    - [core/llms/huggingface_model.md](core/llms/huggingface_model.md)
    - [core/llms/ollama_model.md](core/llms/ollama_model.md)
    - [core/llms/gguf_model.md](core/llms/gguf_model.md)
    - [core/llms/gemini.md](core/llms/gemini.md)
    - [core/llms/open_ai.md](core/llms/open_ai.md)
    - [color.md](color.md)
- **External Packages**: `llama_cpp`