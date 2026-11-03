## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **LLMParamsConfigurator** | [src/ai/core/llms/llm_params_configurator.py](/AgentDocs/ai/core/llms/llm_params_configurator.md) |

The `LLMParamsConfigurator` is a utility class designed to standardize and transform Large Language Model (LLM) generation parameters across different backend ecosystems. It acts as a translation layer that ensures user-provided configuration settings are correctly mapped to the specific naming conventions and requirements of various model loaders.

This component serves as a critical bridge within the LLM orchestration layer. It is primarily used to prepare parameter dictionaries for specialized model implementations, such as [huggingface_model.py](/AgentDocs/ai/core/llms/huggingface_model.md) or [gguf_model.py](/AgentDocs/ai/core/llms/gguf_model.md), ensuring that high-level user intents (like "max tokens") are converted into library-specific arguments (like "max_new_tokens" for Hugging Face).

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `LLMParamsConfigurator` | Class | Manages available LLM properties and provides mapping logic for different model types. |
| `prepare_llm_params(model_type: str, user_params: dict = {})` | Method | Takes a `model_type` ('huggingface' or 'gguf') and a dictionary of `user_params`. Returns a new dictionary with keys mapped to the target library's conventions and invalid parameters filtered out. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class maintains an internal registry of `available_properties` representing the "source of truth" for supported parameters. It uses a nested dictionary, `model_param_compatibility`, to define how these internal keys map to target library keys (e.g., mapping `stop_sequences` to `stop_strings` for Hugging Face). The `prepare_llm_params` method iterates through user input, validates keys against the available properties, and performs the translation if a mapping exists for the requested `model_type`.
- **Side Effects:** This component performs no I/O operations. It communicates warnings to `stdout` via `print` statements when encountering unknown parameters or parameters not supported by the specific `model_type`.
- **Error Handling:** 
    - Raises `ValueError` if a `model_type` is requested that is not defined in `self.model_param_compatibility`.
    - Silently ignores (with a warning) parameters that are not recognized in the core `available_properties` list.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** None.
- **Internal:** None.