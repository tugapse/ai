## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **EngineManager** | [src/ai/services/engine_manager.py](/AgentDocs/ai/services/engine_manager.md) |

The `EngineManager` class is responsible for the lifecycle management of Large Language Model (LLM) configurations and their corresponding runtime instances. It provides a centralized interface for verifying if specific AI engines (such as Ollama, OpenAI, or GGUF-based loaders) are installed on the host system, generating default configuration schemas, and persisting these settings to the filesystem.

Within the broader application architecture, this component acts as a factory and validation layer between raw configuration files and the active model instances used by the agent. It ensures that before any model instantiation attempt occurs, the required environment dependencies are met, preventing runtime crashes during "lazy imports" of heavy model libraries.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `is_engine_installed(module_type, module_name="")` | Static Method | Checks `installed_engines.json` to verify if a specific `ModelType` or `EngineType` is marked as installed. |
| `generate_default_config(model_name, model_type)` | Static Method | Returns a dictionary containing standard default parameters (temperature, top_p, etc.) for a given `ModelType`. |
| `load_config(filepath)` | Static Method | Reads and parses a JSON configuration file from the specified path. |
| `save_config(config, filepath)` | Static Method | Serializes a configuration dictionary to a JSON file at the specified path. |
| `load_model_instance(model_config, system_prompt, tool_registry)` | Static Method | The primary entry point for model creation. Validates the engine status and returns an instantiated `BaseModel` subclass. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses a mapping system to translate `ModelType` and `EngineType` enums into string IDs used within a local `installed_engines.json` file. When loading models, it performs a conditional dispatch (factory pattern) to private helper methods (e.g., `_create_ollama_model`, `_create_gguf_model`) based on the configuration's `model_type`.
- **Side Effects:** 
    - **Filesystem:** Reads from and writes to JSON configuration files. It also searches for `installed_engines.json` in multiple locations (environment variable path, executable directory, or project root).
    - **Logging:** Uses `ai.functions` to log status updates and errors to the console/system logs.
    - **C-Types/FFI:** In `_create_gguf_model`, it uses `ctypes` to interface with `llama_cpp` to redirect internal C-level logging to a Python callback.
- **Error Handling:** 
    - Throws `FileNotFoundError` if a requested config file is missing.
    - Throws `ValueError` if the model configuration is malformed or if the required engine is not marked as installed.
    - Implements a "fail-safe" mechanism in `is_engine_installed` that returns `False` on unexpected exceptions during file reading.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_ENGINE_STATUS_FILE`  An optional environment variable defining the absolute path to the `installed_engines.json` configuration file.

**Module Dependencies:**
- **Standard/External:** `json`, `os`, `sys`, `typing`, `ctypes`, `llama_cpp`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.entities.model_enums](/AgentDocs/ai/entities/model_enums.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.tools.tool_registry](/AgentDocs/ai/tools/tool_registry.md)
    - [ai.color](/AgentDocs/ai/color.md)
    - [ai.core.llms.huggingface_model](/AgentDocs/ai/core/llms/huggingface_model.md)
    - [ai.core.llms.ollama_model](/AgentDocs/ai/core/llms/ollama_model.md)
    - [ai.core.llms.gguf_model](/AgentDocs/ai/core/llms/gguf_model.md)
    - [ai.core.llms.gemini](/AgentDocs/ai/core/llms/gemini.md)
    - [ai.core.llms.open_ai](/AgentDocs/ai/core/llms/open_ai.md)
    - [ai.core.llms.jarvis](/AgentDocs/ai/core/llms/jarvis.md)