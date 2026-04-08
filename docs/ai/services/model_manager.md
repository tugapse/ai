## Module Purpose
This file defines the `ModelManager` class, responsible for managing model configuration files (creation, loading, saving) and instantiating various Large Language Model (LLM) objects based on these configurations, including checks for installed model engines.

## Interface & Exports
*   `ModelManager`: The primary class, intended for external use.
    *   `ModelManager.is_engine_installed(model_type: ModelType, model_name: str = "") -> bool`: Static method to check if a specific model engine is marked as installed.
    *   `ModelManager.generate_default_config(model_name: str, model_type: ModelType) -> dict`: Static method to create a default model configuration dictionary.
    *   `ModelManager.load_config(filepath: str) -> dict`: Static method to load a model configuration from a JSON file.
    *   `ModelManager.save_config(config: dict, filepath: str)`: Static method to save a model configuration dictionary to a JSON file.
    *   `ModelManager.load_model_instance(model_config: dict, system_prompt: str, ollama_host: Optional[str] = None) -> Optional[BaseModel]`: Static method to instantiate an LLM object based on a provided configuration.

## Internal Logic
The `ModelManager` class provides functionalities to:
1.  **Check Engine Installation**: The `is_engine_installed` method determines the project root, constructs a path to `installed_engines.json`, reads this file, and uses a hardcoded `mapping` from `ModelType` to JSON IDs (e.g., `ModelType.GGUF` to "gguf") to verify if a specific engine is marked as "installed". It includes special handling for "vertex" in `ModelType.GEMINI`.
2.  **Generate Default Configuration**: The `generate_default_config` method creates a dictionary with standard model parameters (`max_new_tokens`, `do_sample`, `temperature`, `top_p`, `top_k`, `quantization_bits`), adjusting `temperature` and `top_p` for `ModelType.SEQ2SEQ_LM`.
3.  **Load/Save Configuration**: The `load_config` and `save_config` methods handle reading from and writing to JSON files, respectively, including error handling for file not found or invalid JSON.
4.  **Instantiate Model**: The `load_model_instance` method parses a `model_config` dictionary, validates `model_name` and `model_type`, and performs an `is_engine_installed` check. Based on the `model_type`, it dynamically imports and instantiates the appropriate LLM class (`HuggingFaceModel`, `T5Model`, `OllamaModel`, `GGUFImageLLM`, `GeminiAPIModel`, `OpenAIAPIModel`), passing model parameters and other keyword arguments. For `ModelType.GGUF`, it includes specific `llama_cpp` log suppression.

## Dependencies
*   `json`
*   `os`
*   `sys`
*   `typing.Optional`
*   `functions as func`
*   `entities.model_enums.ModelType`
*   `core.llms.base_llm.ModelParams`
*   `core.llms.base_llm.BaseModel`
*