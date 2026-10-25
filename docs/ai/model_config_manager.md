## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ModelConfigManager |
| Source file | model_config_manager.py |

The **ModelConfigManager** serves as the centralized factory and persistence layer for model-specific configurations within the AI ecosystem. It abstracts the complexity of defining hyperparameter sets and architectural metadata required by different inference engines, ensuring that model parameters are standardized and easily retrievable.

**Functional Mission**
The primary responsibility of **ModelConfigManager** is to automate the generation of valid configuration schemas for various model types (Ollama, Causal LM, and GGUF) and to manage the I/O operations for these configurations via JSON. It solves the problem of manual parameter management by providing "sane defaults" that align with specific model architectures.

**System Context & Integration**
This component acts as a foundational utility used by higher-level orchestration services to prepare the environment for model loading. It provides the necessary configuration dictionaries that downstream modules, such as [Ollama Model](/docs/ai/core/llms/ollama_model.md), [Huggingface Model](/docs/ai/core/llms/huggingface_model.md), or [GGUF Model](/docs/ai/core/llms/gguf_model.md), consume to initialize their respective inference engines. By centralizing these definitions, it ensures consistency across the [Model Orchestrator](/docs/ai/services/model_orchestrator.md).

- **INTERNAL REFERENCES**: [ModelType](/docs/ai/entities/model_enums.md), [Color](/docs/ai/color.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `n_gpu_layers` (Default: `-1`)  Indicates automatic GPU layer allocation for GGUF.
- `n_ctx` (Default: `8192`)  Context window size for GGUF.
- `max_new_tokens` (Default: `4096` for GGUF, `8192` for Causal/Ollama)  Generation limit.
- `temperature` (Default: `0.3` for GGUF, `0.8` for others)  Sampling randomness.
- `top_p` (Default: `0.95`)  Nucleus sampling threshold.
- `top_k` (Default: `50` for GGUF, `30` for others)  Top-k sampling threshold.
- `presence_penalty` (Default: `1.1`)  Penalty for repeating topics.
- `frequency_penalty` (Default: `1.2` for GGUF, `1.1` for others)  Penalty for repeating tokens.
- `quantization_bits` (Default: `4`)  Bit-depth for Causal LM quantization.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `generate_default_config` | Static Method | Orchestrates the creation of a default config dict based on `ModelType`. |
| `load_config` | Static Method | Reads and parses a JSON file into a dictionary with error handling. |
| `save_config` | Static Method | Serializes a configuration dictionary to a JSON file. |
| `_generate_gguf_config` | Private Method | Returns a hardcoded default schema for GGUF models. |
| `_generate_causal_lm_config` | Private Method | Returns a hardcoded default schema for Causal LM models. |
| `_generate_ollama_config` | Private Method | Returns a hardcoded default schema for Ollama models. |

## 4. Execution Logic & Flow
- **Initialization**: The class is stateless, utilizing `@staticmethod` decorators; it requires no instance initialization.
- **Data Path**: 
    1. **Generation**: `model_name` + `model_type` $\rightarrow$ `generate_default_config` $\rightarrow$ Internal `_generate_*_config` $\rightarrow$ Configuration Dictionary.
    2. **Persistence (Save)**: Configuration Dictionary $\rightarrow$ `save_config` $\rightarrow$ JSON File on disk.
    3. **Retrieval (Load)**: JSON File on disk $\rightarrow$ `load_config` $\rightarrow$ Validation/Parsing $\rightarrow$ Configuration Dictionary.
- **Conditional Branching**:
    - `generate_default_config` uses an `if/elif` ladder to route the request to the specific private generator based on the `ModelType` enum.
    - `load_config` implements error branching for `FileNotFoundError`, `json.JSONDecodeError`, and general `Exception` to provide specific console feedback.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `os`, `sys`, `argparse`
- **Internal Modules**: 
    - [ModelType](/docs/ai/entities/model_enums.md)
    - [ai.functions](/docs/ai/functions.md)
    - [Color](/docs/ai/color.md)
- **External Packages**: None identified.